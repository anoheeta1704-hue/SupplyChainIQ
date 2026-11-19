'use client';

import React, { useState, useEffect } from 'react';

interface EventItem {
  id: number;
  event_type: string;
  location?: string;
  timestamp: string;
  description?: string;
}

interface ShipmentDetailsProps {
  shipment: {
    id: number;
    tracking_number: string;
    origin: string;
    destination: string;
    status: string;
    current_location?: string;
    delay_probability?: number;
    predicted_delay_hours?: number;
    risk_level?: string;
    carrier?: { name: string; rating?: number; service_type?: string };
    package_weight?: number;
    package_value?: number;
  } | null;
  events: EventItem[];
}

export default function ShipmentDetailsPanel({ shipment, events }: ShipmentDetailsProps) {
  const [activeTab, setActiveTab] = useState<'general' | 'tracking' | 'alerts' | 'docs'>('general');

  if (!shipment) return null;

  const isHighRisk = (shipment.delay_probability ?? 0) >= 0.7;

  return (
    <div className="bg-white rounded-xl border border-slate-200/90 shadow-sm p-4 sm:p-5 mt-3.5">
      {/* Tab Strip (Matches Reference Screenshot!) */}
      <div className="flex items-center gap-1.5 border-b border-slate-100 pb-3 mb-4">
        {[
          { id: 'general', label: 'General' },
          { id: 'tracking', label: 'Tracking' },
          { id: 'alerts', label: 'Alerts', badge: isHighRisk ? '1' : undefined },
          { id: 'docs', label: 'Documents' },
        ].map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id as any)}
            className={`px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all flex items-center gap-1.5 ${
              activeTab === tab.id
                ? 'bg-primary-50 text-primary-600 border border-primary-200/60'
                : 'text-slate-500 hover:text-slate-800 hover:bg-slate-50'
            }`}
          >
            <span>{tab.label}</span>
            {tab.badge && (
              <span className="w-4 h-4 rounded-full bg-red-500 text-white text-[10px] flex items-center justify-center font-bold">
                {tab.badge}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Tab 1: General Info */}
      {activeTab === 'general' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-sm font-bold text-slate-900">General Info</h3>
              <p className="text-[11px] text-slate-400">Live telematics • Updated 2 mins ago</p>
            </div>
            <div className="flex items-center gap-1 border border-slate-200 px-2.5 py-1 rounded-lg text-xs font-semibold text-slate-700 bg-slate-50">
              <span>‹</span>
              <span>Today</span>
              <span>›</span>
            </div>
          </div>

          {/* Telemetry Speed & Performance Wave Graph (Mirrors Reference SVG line!) */}
          <div className="bg-slate-50/80 rounded-xl p-3 border border-slate-100">
            <div className="flex justify-between text-xs text-slate-500 font-medium mb-1">
              <span>Fleet Velocity Telemetry</span>
              <span className="text-primary-600 font-bold">64 km/h avg</span>
            </div>
            <div className="h-14 w-full">
              <svg viewBox="0 0 300 60" className="w-full h-full overflow-visible">
                <defs>
                  <linearGradient id="telemetryGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#3B82F6" stopOpacity="0.35" />
                    <stop offset="100%" stopColor="#3B82F6" stopOpacity="0.0" />
                  </linearGradient>
                </defs>
                <path
                  d="M0,45 Q30,15 60,35 T120,20 T180,40 T240,15 T300,30 L300,60 L0,60 Z"
                  fill="url(#telemetryGrad)"
                />
                <path
                  d="M0,45 Q30,15 60,35 T120,20 T180,40 T240,15 T300,30"
                  fill="none"
                  stroke="#2563EB"
                  strokeWidth="2.5"
                  strokeLinecap="round"
                />
                <circle cx="240" cy="15" r="4" fill="#2563EB" stroke="white" strokeWidth="2" />
              </svg>
            </div>
          </div>

          {/* Metadata Grid */}
          <div className="grid grid-cols-2 gap-3 text-xs pt-1">
            <div className="bg-slate-50 p-2.5 rounded-lg border border-slate-100">
              <div className="text-slate-400 text-[10px] uppercase font-semibold">Carrier Partner</div>
              <div className="font-bold text-slate-800 mt-0.5">{shipment.carrier?.name || 'BlueDart Logistics'}</div>
              <div className="text-[10px] text-emerald-600 font-medium mt-0.5">★ 4.8 Rating • Air Cargo</div>
            </div>
            <div className="bg-slate-50 p-2.5 rounded-lg border border-slate-100">
              <div className="text-slate-400 text-[10px] uppercase font-semibold">Current Location</div>
              <div className="font-bold text-slate-800 mt-0.5 truncate">{shipment.current_location || 'En route on corridor'}</div>
              <div className="text-[10px] text-primary-600 font-medium mt-0.5">Simulated GPS lock</div>
            </div>
          </div>
        </div>
      )}

      {/* Tab 2: Tracking Milestone Timeline */}
      {activeTab === 'tracking' && (
        <div className="space-y-3">
          <div className="text-xs font-bold text-slate-900 mb-2">Milestone Event Log ({events.length})</div>
          {events.length === 0 ? (
            <p className="text-xs text-slate-400 py-3 text-center">No tracking events recorded yet.</p>
          ) : (
            <div className="relative pl-5 space-y-3 text-xs border-l-2 border-slate-200 ml-2">
              {events.map((ev, i) => (
                <div key={ev.id || i} className="relative">
                  <span className={`absolute -left-[27px] top-1 w-3 h-3 rounded-full border-2 border-white ${
                    ev.event_type.includes('DELAY') ? 'bg-red-500' :
                    ev.event_type === 'DELIVERED' ? 'bg-emerald-500' : 'bg-primary-500'
                  }`} />
                  <div className="font-bold text-slate-800">{ev.event_type}</div>
                  <div className="text-[11px] text-slate-600">{ev.description}</div>
                  <div className="text-[10px] text-slate-400 mt-0.5">
                    📍 {ev.location || 'National Highway'} • {new Date(ev.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Tab 3: Alerts & Delay Predictions */}
      {activeTab === 'alerts' && (
        <div className="space-y-3">
          <div className="text-xs font-bold text-slate-900">Predictive Delay AI Insights</div>
          <div className={`p-3 rounded-xl border ${
            isHighRisk ? 'bg-red-50/70 border-red-200 text-red-800' : 'bg-slate-50 border-slate-200 text-slate-800'
          }`}>
            <div className="flex items-center justify-between font-bold text-xs mb-1">
              <span>Risk Classification</span>
              <span className={`px-2 py-0.5 rounded-full text-[10px] ${
                isHighRisk ? 'bg-red-200 text-red-900' : 'bg-emerald-100 text-emerald-800'
              }`}>
                {shipment.risk_level || 'LOW'} RISK
              </span>
            </div>
            <div className="text-xs mb-2">
              Delay Probability: <b>{Math.round((shipment.delay_probability ?? 0.15) * 100)}%</b>
              {shipment.predicted_delay_hours ? ` • Est Delay: +${shipment.predicted_delay_hours} hrs` : ''}
            </div>
            <div className="text-[11px] text-slate-600 bg-white/80 p-2 rounded-lg border border-slate-100">
              <b>Heuristic Factors:</b> Weather Congestion on NH corridors, Interstate Highway Checkpoint queues.
            </div>
          </div>
        </div>
      )}

      {/* Tab 4: Documents */}
      {activeTab === 'docs' && (
        <div className="text-xs space-y-2">
          <div className="flex items-center justify-between p-2.5 rounded-lg border border-slate-200 bg-slate-50">
            <span className="font-semibold text-slate-700">📄 e-Way_Bill_{shipment.tracking_number}.pdf</span>
            <span className="text-primary-600 font-bold cursor-pointer hover:underline">Download</span>
          </div>
          <div className="flex items-center justify-between p-2.5 rounded-lg border border-slate-200 bg-slate-50">
            <span className="font-semibold text-slate-700">📋 Linehaul_Manifest.json</span>
            <span className="text-primary-600 font-bold cursor-pointer hover:underline">View</span>
          </div>
        </div>
      )}
    </div>
  );
}
