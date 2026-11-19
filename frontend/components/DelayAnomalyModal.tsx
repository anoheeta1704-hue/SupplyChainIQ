'use client';

import React, { useState, useEffect } from 'react';
import { API_BASE } from '@/lib/config';

interface ShipmentSummary {
  tracking_number: string;
  origin: string;
  destination: string;
  status?: string;
}

interface DelayAnomalyModalProps {
  isOpen: boolean;
  onClose: () => void;
  shipments: ShipmentSummary[];
  initialTrackingNumber?: string;
  onAnomalyInjected: (data: any) => void;
}

const ANOMALY_SCENARIOS = [
  {
    label: 'Severe rainfall/flooding',
    value: 'Severe rainfall and highway flooding',
    impact: 'Recalculates delay risk to HIGH (89%), status -> DELAYED, creates WEATHER_DELAY event (+14.5 hrs)',
    badge: '🌧️ Weather',
  },
  {
    label: 'Traffic congestion',
    value: 'Heavy traffic congestion & arterial bottleneck',
    impact: 'Recalculates delay risk to HIGH (82%), status -> DELAYED, creates TRAFFIC_DELAY event (+7.5 hrs)',
    badge: '🚗 Traffic',
  },
  {
    label: 'Vehicle breakdown',
    value: 'Linehaul vehicle mechanical breakdown',
    impact: 'Recalculates delay risk to CRITICAL (94%), status -> DELAYED, creates MECHANICAL_FAILURE event (+18.0 hrs)',
    badge: '⚠️ Breakdown',
  },
  {
    label: 'Warehouse delay',
    value: 'Warehouse sorting backlog and cross-dock delay',
    impact: 'Recalculates delay risk to HIGH (74%), status -> AT_WAREHOUSE, creates ARRIVED_WAREHOUSE event (+8.0 hrs)',
    badge: '🏢 Warehouse',
  },
  {
    label: 'Route diversion',
    value: 'Highway road closure and route diversion',
    impact: 'Recalculates delay risk to MEDIUM (68%), status -> IN_TRANSIT, creates ROUTE_DIVERSION event (+4.5 hrs)',
    badge: '🔄 Diversion',
  },
];

export default function DelayAnomalyModal({
  isOpen,
  onClose,
  shipments = [],
  initialTrackingNumber,
  onAnomalyInjected,
}: DelayAnomalyModalProps) {
  const [availableShipments, setAvailableShipments] = useState<ShipmentSummary[]>(shipments);
  const [selectedTracking, setSelectedTracking] = useState<string>('');
  const [selectedScenario, setSelectedScenario] = useState<string>(ANOMALY_SCENARIOS[0].value);
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Sync available shipments from prop or fallback fetch
  useEffect(() => {
    if (!isOpen) return;

    setErrorMsg(null);

    if (shipments && shipments.length > 0) {
      setAvailableShipments(shipments);
      const initial = initialTrackingNumber && shipments.some((s) => s.tracking_number === initialTrackingNumber)
        ? initialTrackingNumber
        : shipments[0]?.tracking_number || '';
      setSelectedTracking(initial);
    } else {
      // Fallback: Fetch directly from API if parent passed empty array
      fetch(`${API_BASE}/api/shipments?page_size=50`)
        .then((res) => {
          if (!res.ok) throw new Error(`HTTP ${res.status}`);
          return res.json();
        })
        .then((data) => {
          const items = data.items || [];
          setAvailableShipments(items);
          if (items.length > 0) {
            const initial = initialTrackingNumber && items.some((s: any) => s.tracking_number === initialTrackingNumber)
              ? initialTrackingNumber
              : items[0]?.tracking_number || '';
            setSelectedTracking(initial);
          }
        })
        .catch((err) => {
          console.error('Failed to load shipments for anomaly modal:', err);
          setErrorMsg('Unable to load shipments from backend. Please verify server connection.');
        });
    }
  }, [isOpen, shipments, initialTrackingNumber]);

  if (!isOpen) return null;

  const currentScenarioObj = ANOMALY_SCENARIOS.find((s) => s.value === selectedScenario) || ANOMALY_SCENARIOS[0];

  const handleInject = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedTracking) {
      setErrorMsg('Please select a shipment to inject anomaly.');
      return;
    }
    setLoading(true);
    setErrorMsg(null);

    try {
      const res = await fetch(`${API_BASE}/api/simulator/inject-anomaly`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          tracking_number: selectedTracking,
          reason: selectedScenario,
        }),
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || `Failed to inject anomaly (${res.status})`);
      }

      const data = await res.json();
      onAnomalyInjected(data);
      onClose();
    } catch (err: any) {
      console.error('Error injecting delay anomaly:', err);
      setErrorMsg(err.message || 'Error communicating with backend simulator.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-[1000] flex items-center justify-center p-4 bg-slate-950/60 backdrop-blur-sm animate-fade-in">
      <div className="bg-white rounded-2xl shadow-2xl max-w-lg w-full overflow-hidden border border-slate-200">
        {/* Header */}
        <div className="bg-gradient-to-r from-amber-600 to-amber-700 px-6 py-4 flex items-center justify-between text-white">
          <div className="flex items-center gap-2.5">
            <span className="text-2xl">⚡</span>
            <div>
              <h2 className="text-base font-bold">Inject Delay Anomaly</h2>
              <p className="text-xs text-amber-100">Simulate real-time logistics disruptions & risk score updates</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-amber-200 hover:text-white p-1.5 rounded-lg hover:bg-amber-600/50 transition-colors"
          >
            ✕
          </button>
        </div>

        {/* Error message */}
        {errorMsg && (
          <div className="mx-6 mt-4 p-3 bg-red-50 border border-red-200 rounded-xl text-xs text-red-700 flex items-center gap-2">
            <span>⚠️</span>
            <span>{errorMsg}</span>
          </div>
        )}

        {/* Form */}
        <form onSubmit={handleInject} className="p-6 space-y-4 text-xs sm:text-sm">
          {/* Select Shipment */}
          <div>
            <label className="block font-semibold text-slate-700 mb-1">Select Shipment</label>
            {availableShipments.length === 0 ? (
              <div className="p-3 bg-slate-100 rounded-lg text-slate-500 text-xs flex items-center justify-between">
                <span>Loading active shipments...</span>
                <div className="w-4 h-4 border-2 border-amber-600 border-t-transparent rounded-full animate-spin" />
              </div>
            ) : (
              <select
                value={selectedTracking}
                onChange={(e) => setSelectedTracking(e.target.value)}
                className="w-full bg-slate-50 border border-slate-300 rounded-lg px-3 py-2 text-slate-900 font-medium focus:outline-none focus:ring-2 focus:ring-amber-500 transition-all cursor-pointer"
              >
                {availableShipments.map((s) => (
                  <option key={s.tracking_number} value={s.tracking_number}>
                    {s.tracking_number} • {s.origin} ➔ {s.destination} ({s.status || 'Active'})
                  </option>
                ))}
              </select>
            )}
          </div>

          {/* Anomaly Scenario Dropdown */}
          <div>
            <label className="block font-semibold text-slate-700 mb-1">Disruption Scenario</label>
            <select
              value={selectedScenario}
              onChange={(e) => setSelectedScenario(e.target.value)}
              className="w-full bg-slate-50 border border-slate-300 rounded-lg px-3 py-2 text-slate-900 font-medium focus:outline-none focus:ring-2 focus:ring-amber-500 transition-all cursor-pointer"
            >
              {ANOMALY_SCENARIOS.map((sc) => (
                <option key={sc.label} value={sc.value}>
                  {sc.badge} {sc.label}
                </option>
              ))}
            </select>
          </div>

          {/* Scenario Details & Live Prediction Preview */}
          <div className="p-3.5 bg-amber-50/80 rounded-xl border border-amber-200/90 text-xs text-amber-900 space-y-1.5">
            <div className="font-bold flex items-center gap-1.5">
              <span>{currentScenarioObj.badge}</span>
              <span>Predicted Impact:</span>
            </div>
            <p className="text-amber-800 leading-relaxed font-normal">{currentScenarioObj.impact}</p>
            <div className="text-[11px] text-amber-700/90 pt-1 border-t border-amber-200/60 flex items-center gap-1">
              <span>✓ Persists tracking event & alert to database</span>
              <span>• Updates map & card in real-time</span>
            </div>
          </div>

          {/* Action buttons */}
          <div className="pt-3 flex items-center justify-end gap-3 border-t border-slate-100">
            <button
              type="button"
              onClick={onClose}
              disabled={loading}
              className="px-4 py-2 rounded-xl text-slate-600 hover:bg-slate-100 font-medium transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading || availableShipments.length === 0}
              className="bg-amber-600 hover:bg-amber-500 disabled:bg-slate-300 text-white font-bold px-5 py-2 rounded-xl shadow-md transition-all flex items-center gap-2"
            >
              {loading ? (
                <>
                  <div className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  <span>Injecting...</span>
                </>
              ) : (
                <>
                  <span>⚡</span>
                  <span>Trigger Delay</span>
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
