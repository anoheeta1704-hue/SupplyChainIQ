'use client';

import React, { useState, useEffect, useRef } from 'react';
import dynamic from 'next/dynamic';

import Navbar from '@/components/Navbar';
import FilterBar from '@/components/FilterBar';
import TitleBar from '@/components/TitleBar';
import ShipmentCard from '@/components/ShipmentCard';
import ShipmentSummaryCards from '@/components/ShipmentSummaryCards';
import ShipmentDetailsPanel from '@/components/ShipmentDetailsPanel';
import ShipmentTable from '@/components/ShipmentTable';
import AddShipmentModal from '@/components/AddShipmentModal';
import DelayAnomalyModal from '@/components/DelayAnomalyModal';
import { API_BASE, WS_BASE } from '@/lib/config';

// Dynamically import Leaflet Map (SSR False)
const InteractiveMap = dynamic(() => import('@/components/InteractiveMap'), {
  ssr: false,
  loading: () => (
    <div className="w-full h-full min-h-[480px] bg-slate-100 rounded-xl flex items-center justify-center border border-slate-200">
      <div className="flex flex-col items-center gap-2 text-slate-400">
        <div className="w-8 h-8 border-4 border-primary-500 border-t-transparent rounded-full animate-spin" />
        <span className="text-xs font-semibold">Initializing Interactive Leaflet Map...</span>
      </div>
    </div>
  ),
});

export default function DashboardPage() {
  const [shipments, setShipments] = useState<any[]>([]);
  const [selectedShipment, setSelectedShipment] = useState<any | null>(null);
  const [events, setEvents] = useState<any[]>([]);
  const [routesData, setRoutesData] = useState<Record<string, any>>({});
  const [loading, setLoading] = useState<boolean>(true);

  // Filters & Views
  const [viewMode, setViewMode] = useState<'map' | 'list'>('map');
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [carrierFilter, setCarrierFilter] = useState('ALL');
  const [riskFilter, setRiskFilter] = useState('ALL');

  // Simulator controls
  const [isSimRunning, setIsSimRunning] = useState(false);
  const [simSpeed, setSimSpeed] = useState(1);
  const [tickCount, setTickCount] = useState(0);

  // Modals
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [isAnomalyModalOpen, setIsAnomalyModalOpen] = useState(false);
  const [anomalyTrackingTarget, setAnomalyTrackingTarget] = useState<string>('');
  const [isRefreshing, setIsRefreshing] = useState(false);

  // Alert toast
  const [activeAlert, setActiveAlert] = useState<{ title: string; message: string } | null>(null);

  // Fetch initial shipments and routes (with cache busting)
  const fetchShipments = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/shipments?page_size=50&_t=${Date.now()}`, {
        cache: 'no-store',
        headers: {
          'Cache-Control': 'no-cache, no-store, must-revalidate',
          'Pragma': 'no-cache',
        },
      });
      if (res.ok) {
        const data = await res.json();
        const items = data.items || [];
        setShipments(items);
        // Synchronize selectedShipment with fresh data from database
        setSelectedShipment((curr: any) => {
          if (!curr && items.length > 0) return items[0];
          if (curr) {
            const fresh = items.find((it: any) => it.id === curr.id || it.tracking_number === curr.tracking_number);
            return fresh || items[0] || null;
          }
          return null;
        });
      }
    } catch (err) {
      console.error('Error fetching shipments:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleOpenAnomaly = (tracking?: string) => {
    if (tracking) {
      setAnomalyTrackingTarget(tracking);
    } else if (selectedShipment?.tracking_number) {
      setAnomalyTrackingTarget(selectedShipment.tracking_number);
    } else if (shipments.length > 0) {
      setAnomalyTrackingTarget(shipments[0].tracking_number);
    }
    setIsAnomalyModalOpen(true);
  };

  const fetchRoutes = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/shipments/routes?_t=${Date.now()}`, {
        cache: 'no-store',
      });
      if (res.ok) {
        const data = await res.json();
        setRoutesData(data);
      }
    } catch (err) {
      console.error('Error fetching routes:', err);
    }
  };

  const fetchSimulatorStatus = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/simulator/status?_t=${Date.now()}`, {
        cache: 'no-store',
      });
      if (res.ok) {
        const data = await res.json();
        setIsSimRunning(Boolean(data.is_running));
        if (data.speed) setSimSpeed(data.speed);
        if (data.tick_count !== undefined) setTickCount(data.tick_count);
      } else {
        setIsSimRunning(false);
      }
    } catch (err) {
      setIsSimRunning(false);
    }
  };

  const fetchShipmentEvents = async (shipmentId: number) => {
    try {
      const res = await fetch(`${API_BASE}/api/shipments/${shipmentId}/events?_t=${Date.now()}`, {
        cache: 'no-store',
      });
      if (res.ok) {
        const evs = await res.json();
        setEvents(evs);
      }
    } catch (err) {
      console.error('Error fetching events:', err);
    }
  };

  useEffect(() => {
    fetchShipments();
    fetchRoutes();
    fetchSimulatorStatus();
  }, []);

  // Fetch events when selected shipment changes
  useEffect(() => {
    if (selectedShipment) {
      fetchShipmentEvents(selectedShipment.id);
    }
  }, [selectedShipment?.id]);

  // Real-time WebSocket Connection
  useEffect(() => {
    let ws: WebSocket | null = null;
    let reconnectTimeout: any = null;

    const connectWs = () => {
      try {
        ws = new WebSocket(`${WS_BASE}/api/ws/tracking`);

        ws.onopen = () => {
          console.log('Connected to real-time tracking WebSocket');
        };

        ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            if (data.type === 'INIT') {
              setIsSimRunning(Boolean(data.is_running));
              if (data.speed) setSimSpeed(data.speed);
              if (data.tick !== undefined) setTickCount(data.tick);
            } else if (data.type === 'TICK_UPDATE') {
              setTickCount(data.tick);
              if (data.updated_shipments && data.updated_shipments.length > 0) {
                setShipments((prev) =>
                  prev.map((s) => {
                    const match = data.updated_shipments.find((u: any) => u.id === s.id);
                    if (match) {
                      return {
                        ...s,
                        status: match.status,
                        current_location: match.current_location,
                        current_latitude: match.lat,
                        current_longitude: match.lng,
                        delay_probability: match.delay_probability,
                        risk_level: match.risk_level,
                      };
                    }
                    return s;
                  })
                );

                // Update selected shipment if it moved
                setSelectedShipment((curr: any) => {
                  if (!curr) return curr;
                  const match = data.updated_shipments.find((u: any) => u.id === curr.id);
                  if (match) {
                    return {
                      ...curr,
                      status: match.status,
                      current_location: match.current_location,
                      current_latitude: match.lat,
                      current_longitude: match.lng,
                      delay_probability: match.delay_probability,
                      risk_level: match.risk_level,
                    };
                  }
                  return curr;
                });
              }

              // If there are new events for selected shipment, re-fetch events
              if (data.new_events && data.new_events.length > 0) {
                if (selectedShipment) {
                  fetchShipmentEvents(selectedShipment.id);
                }
              }
            } else if (data.type === 'ALERT_TRIGGERED') {
              setActiveAlert({
                title: `🚨 Delay Alert (${data.tracking_number})`,
                message: `${data.reason} detected. Status updated to ${data.status}.`,
              });
              setTimeout(() => setActiveAlert(null), 6000);
              fetchShipments();
            } else if (data.type === 'STATUS_CHANGE') {
              setIsSimRunning(data.is_running);
            } else if (data.type === 'SPEED_CHANGE') {
              setSimSpeed(data.speed);
            } else if (data.type === 'RESET') {
              fetchShipments();
            }
          } catch (e) {
            console.error('WS parse error:', e);
          }
        };

        ws.onclose = () => {
          reconnectTimeout = setTimeout(connectWs, 3000);
        };
      } catch (err) {
        reconnectTimeout = setTimeout(connectWs, 3000);
      }
    };

    connectWs();

    // Fallback polling every 5s if WS disconnects
    const pollInterval = setInterval(() => {
      if (!ws || ws.readyState !== WebSocket.OPEN) {
        fetchShipments();
      }
    }, 5000);

    return () => {
      if (ws) ws.close();
      clearTimeout(reconnectTimeout);
      clearInterval(pollInterval);
    };
  }, [selectedShipment?.id]);

  // Simulator controls
  const handleToggleSim = async () => {
    try {
      const endpoint = isSimRunning ? 'stop' : 'start';
      const res = await fetch(`${API_BASE}/api/simulator/${endpoint}`, { method: 'POST' });
      if (res.ok) {
        setIsSimRunning(!isSimRunning);
      }
    } catch (err) {
      console.error('Error toggling simulator:', err);
    }
  };

  const handleStepSim = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/simulator/step`, { method: 'POST' });
      if (res.ok) {
        const data = await res.json();
        if (data.payload?.updated_shipments) {
          setShipments((prev) =>
            prev.map((s) => {
              const match = data.payload.updated_shipments.find((u: any) => u.id === s.id);
              return match
                ? {
                    ...s,
                    status: match.status,
                    current_location: match.current_location,
                    current_latitude: match.lat,
                    current_longitude: match.lng,
                    delay_probability: match.delay_probability,
                    risk_level: match.risk_level,
                  }
                : s;
            })
          );
        }
        await fetchShipments();
        if (selectedShipment?.id) {
          await fetchShipmentEvents(selectedShipment.id);
        }
      }
    } catch (err) {
      console.error('Error stepping simulator:', err);
    }
  };

  const handleChangeSpeed = async (spd: number) => {
    try {
      setSimSpeed(spd);
      await fetch(`${API_BASE}/api/simulator/speed`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ speed: spd }),
      });
    } catch (err) {
      console.error('Error changing speed:', err);
    }
  };

  const handleResetSim = async () => {
    try {
      setLoading(true);
      await fetch(`${API_BASE}/api/simulator/reset`, { method: 'POST' });
      await fetchShipments();
      await fetchRoutes();
      await fetchSimulatorStatus();
      setActiveAlert({
        title: '↺ Simulation Reset',
        message: 'All 7 Indian logistics routes reset to starting hubs and initial coordinates.',
      });
      setTimeout(() => setActiveAlert(null), 4000);
    } catch (err) {
      console.error('Error resetting simulator:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleRefresh = async () => {
    try {
      setIsRefreshing(true);
      // Trigger fresh shipment data generation & live telematics in database
      const stepRes = await fetch(`${API_BASE}/api/simulator/refresh`, { method: 'POST' });
      if (stepRes.ok) {
        const stepData = await stepRes.json();
        if (stepData?.payload?.updated_shipments) {
          setShipments((prev) =>
            prev.map((s) => {
              const match = stepData.payload.updated_shipments.find((u: any) => u.id === s.id);
              return match
                ? {
                    ...s,
                    tracking_number: match.tracking_number || s.tracking_number,
                    status: match.status,
                    current_location: match.current_location,
                    current_latitude: match.lat,
                    current_longitude: match.lng,
                    delay_probability: match.delay_probability,
                    risk_level: match.risk_level,
                    package_weight: match.package_weight || s.package_weight,
                    package_value: match.package_value || s.package_value,
                  }
                : s;
            })
          );
        }
      }
      await fetchShipments();
      await fetchRoutes();
      await fetchSimulatorStatus();
      if (selectedShipment?.id) {
        await fetchShipmentEvents(selectedShipment.id);
      }
      setActiveAlert({
        title: '↻ Fresh Shipment Data Generated',
        message: 'Generated new live telematics, updated GPS waypoints, and milestone scans in database.',
      });
      setTimeout(() => setActiveAlert(null), 4000);
    } catch (err) {
      console.error('Error refreshing and generating shipment data:', err);
    } finally {
      setIsRefreshing(false);
    }
  };

  const handleAnomalyInjected = (data: any) => {
    setActiveAlert({
      title: `⚡ ${data.title || 'Delay Anomaly Triggered'} (${data.tracking_number})`,
      message: `${data.message || data.reason}. Status: ${data.status}, Risk: ${Math.round((data.delay_probability || 0.85) * 100)}%`,
    });
    setTimeout(() => setActiveAlert(null), 8000);
    fetchShipments();
    if (selectedShipment?.id) {
      fetchShipmentEvents(selectedShipment.id);
    }
  };

  // Filtered shipments
  const filteredShipments = shipments.filter((s) => {
    // Search filter
    if (search.trim()) {
      const q = search.toLowerCase();
      const matchId = s.tracking_number.toLowerCase().includes(q);
      const matchOrigin = s.origin.toLowerCase().includes(q);
      const matchDest = s.destination.toLowerCase().includes(q);
      const matchCarrier = s.carrier?.name?.toLowerCase().includes(q);
      const matchLoc = s.current_location?.toLowerCase().includes(q);
      if (!matchId && !matchOrigin && !matchDest && !matchCarrier && !matchLoc) {
        return false;
      }
    }

    // Status filter
    if (statusFilter !== 'ALL') {
      if (s.status !== statusFilter) return false;
    }

    // Carrier filter
    if (carrierFilter !== 'ALL') {
      if (!s.carrier?.name?.toLowerCase().includes(carrierFilter.toLowerCase())) return false;
    }

    // Risk filter
    if (riskFilter !== 'ALL') {
      if (riskFilter === 'HIGH' && (s.delay_probability ?? 0) < 0.7) return false;
      if (riskFilter === 'MEDIUM' && ((s.delay_probability ?? 0) < 0.3 || (s.delay_probability ?? 0) >= 0.7)) return false;
      if (riskFilter === 'LOW' && (s.delay_probability ?? 0) >= 0.3) return false;
    }

    return true;
  });

  const statusCounts = {
    total: shipments.length,
    inTransit: shipments.filter((s) => s.status === 'IN_TRANSIT').length,
    delayed: shipments.filter((s) => s.status === 'DELAYED' || (s.delay_probability ?? 0) >= 0.7).length,
  };

  return (
    <div className="min-h-screen bg-slate-100 flex flex-col font-sans">
      {/* 1. Dark Navy Top Navigation */}
      <Navbar />

      {/* 2. Dark Navy Filter Bar */}
      <FilterBar
        search={search}
        onSearchChange={setSearch}
        statusFilter={statusFilter}
        onStatusFilterChange={setStatusFilter}
        carrierFilter={carrierFilter}
        onCarrierFilterChange={setCarrierFilter}
        riskFilter={riskFilter}
        onRiskFilterChange={setRiskFilter}
        statusCounts={statusCounts}
      />

      {/* 3. Title & Action Bar */}
      <TitleBar
        viewMode={viewMode}
        onViewModeChange={setViewMode}
        onOpenAddModal={() => setIsAddModalOpen(true)}
        onOpenAnomalyModal={() => handleOpenAnomaly()}
        isSimRunning={isSimRunning}
        simSpeed={simSpeed}
        onToggleSim={handleToggleSim}
        onStepSim={handleStepSim}
        onChangeSpeed={handleChangeSpeed}
        onResetSim={handleResetSim}
        onRefresh={handleRefresh}
        isRefreshing={isRefreshing}
      />

      {/* Alert Banner / Toast Notification */}
      {activeAlert && (
        <div className="fixed top-20 right-6 z-[1200] max-w-md bg-red-600 text-white p-4 rounded-xl shadow-2xl border border-red-400 flex items-start gap-3 animate-slide-in">
          <span className="text-xl">⚠️</span>
          <div className="flex-1">
            <h4 className="font-bold text-sm">{activeAlert.title}</h4>
            <p className="text-xs text-red-100 mt-0.5">{activeAlert.message}</p>
          </div>
          <button onClick={() => setActiveAlert(null)} className="text-red-200 hover:text-white text-xs">
            ✕
          </button>
        </div>
      )}

      {/* 4. Main Content Area (Clean White / Light Slate Canvas) */}
      <main className="flex-1 max-w-[1720px] w-full mx-auto p-4 sm:p-6 lg:p-8">
        {loading ? (
          <div className="flex flex-col items-center justify-center py-24 gap-3 text-slate-400">
            <div className="w-10 h-10 border-4 border-primary-600 border-t-transparent rounded-full animate-spin" />
            <p className="text-sm font-semibold">Loading live shipments from database...</p>
          </div>
        ) : viewMode === 'map' ? (
          /* ============================================================
             MAP VIEW (SPLIT PANEL MATCHING REFERENCE SCREENSHOT)
             ============================================================ */
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 items-start">
            {/* Left Column: Shipment Cards + Details Panel */}
            <div className="lg:col-span-5 xl:col-span-4 flex flex-col space-y-3.5">
              <div className="flex items-center justify-between px-1">
                <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">
                  Active Shipments ({filteredShipments.length})
                </span>
                <button
                  type="button"
                  disabled={isRefreshing}
                  onClick={handleRefresh}
                  className="text-[11px] text-primary-600 font-semibold hover:underline flex items-center gap-1 disabled:opacity-50"
                >
                  <span className={isRefreshing ? "inline-block animate-spin" : ""}>↻</span>
                  <span>{isRefreshing ? "Refreshing..." : "Refresh"}</span>
                </button>
              </div>

              {/* Scrollable Shipment Cards */}
              <div className="space-y-3 max-h-[460px] overflow-y-auto pr-1">
                {filteredShipments.length === 0 ? (
                  <div className="bg-white rounded-xl p-8 text-center text-slate-400 text-xs border border-slate-200">
                    No shipments match the selected filters.
                  </div>
                ) : (
                  filteredShipments.map((s) => (
                    <ShipmentCard
                      key={s.id}
                      shipment={s}
                      isSelected={selectedShipment?.id === s.id}
                      onSelect={() => setSelectedShipment(s)}
                    />
                  ))
                )}
              </div>

              {/* General Info / Tracking Milestones / Telemetry Tabs */}
              {selectedShipment && (
                <ShipmentDetailsPanel shipment={selectedShipment} events={events} />
              )}
            </div>

            {/* Right Column: Top 3 Metric Summary Cards + Interactive Map */}
            <div className="lg:col-span-7 xl:col-span-8 flex flex-col">
              {/* 3 Summary Cards (Mirrors Reference!) */}
              <ShipmentSummaryCards shipment={selectedShipment} allShipments={shipments} />

              {/* Interactive Map (Leaflet) */}
              <div className="w-full h-[540px] xl:h-[580px]">
                <InteractiveMap
                  shipments={shipments}
                  selectedShipment={selectedShipment}
                  routesData={routesData}
                  onSelectShipment={(s) => setSelectedShipment(s)}
                />
              </div>
            </div>
          </div>
        ) : (
          /* ============================================================
             LIST VIEW (POLISHED TABLE MODE)
             ============================================================ */
          <div className="space-y-4">
            <ShipmentSummaryCards shipment={selectedShipment} allShipments={shipments} />
            <ShipmentTable
              shipments={filteredShipments}
              onSelectAndSwitchToMap={(s) => {
                setSelectedShipment(s);
                setViewMode('map');
              }}
              onInjectDelay={(tracking) => {
                handleOpenAnomaly(tracking);
              }}
            />
          </div>
        )}
      </main>

      {/* Add Shipment Modal */}
      <AddShipmentModal
        isOpen={isAddModalOpen}
        onClose={() => setIsAddModalOpen(false)}
        onCreated={(newShipment) => {
          fetchShipments();
          setSelectedShipment(newShipment);
          setViewMode('map');
        }}
      />

      {/* Delay Anomaly Injection Modal */}
      <DelayAnomalyModal
        isOpen={isAnomalyModalOpen}
        onClose={() => setIsAnomalyModalOpen(false)}
        shipments={shipments}
        initialTrackingNumber={anomalyTrackingTarget}
        onAnomalyInjected={handleAnomalyInjected}
      />
    </div>
  );
}
