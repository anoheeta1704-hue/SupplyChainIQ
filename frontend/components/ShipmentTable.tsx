'use client';

import React from 'react';

interface ShipmentItem {
  id: number;
  tracking_number: string;
  origin: string;
  destination: string;
  status: string;
  current_location?: string;
  delay_probability?: number;
  predicted_delay_hours?: number;
  risk_level?: string;
  carrier?: { name: string };
  package_weight?: number;
  package_value?: number;
  expected_delivery?: string;
  created_at?: string;
}

interface ShipmentTableProps {
  shipments: ShipmentItem[];
  onSelectAndSwitchToMap: (s: ShipmentItem) => void;
  onInjectDelay: (trackingNumber: string) => void;
}

export default function ShipmentTable({
  shipments,
  onSelectAndSwitchToMap,
  onInjectDelay,
}: ShipmentTableProps) {
  const getStatusBadge = (status: string, delayProb?: number) => {
    const isDelayed = status === 'DELAYED' || (delayProb ?? 0) >= 0.7;
    if (isDelayed) {
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-red-50 text-red-600 border border-red-200">
          <span className="w-1.5 h-1.5 rounded-full bg-red-500 animate-pulse"></span>
          Delayed
        </span>
      );
    }
    switch (status) {
      case 'IN_TRANSIT':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-sky-50 text-primary-600 border border-primary-200">
            <span className="w-1.5 h-1.5 rounded-full bg-primary-500 animate-pulse"></span>
            In transit
          </span>
        );
      case 'DELIVERED':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-600 border border-emerald-200">
            ✓ Delivered
          </span>
        );
      case 'AT_WAREHOUSE':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-slate-100 text-slate-700 border border-slate-200">
            Stationary
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-blue-50 text-blue-600 border border-blue-200">
            {status}
          </span>
        );
    }
  };

  return (
    <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse text-xs sm:text-sm">
          <thead>
            <tr className="bg-slate-50/80 border-b border-slate-200 text-slate-500 text-[11px] uppercase tracking-wider font-semibold">
              <th className="py-3 px-4">Shipment ID</th>
              <th className="py-3 px-4">Status</th>
              <th className="py-3 px-4">Route</th>
              <th className="py-3 px-4">Carrier</th>
              <th className="py-3 px-4">Weight & Value</th>
              <th className="py-3 px-4">Delay Risk</th>
              <th className="py-3 px-4">ETA</th>
              <th className="py-3 px-4 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 text-slate-700">
            {shipments.map((s) => (
              <tr
                key={s.id}
                className="hover:bg-slate-50/70 transition-colors cursor-pointer group"
                onClick={() => onSelectAndSwitchToMap(s)}
              >
                <td className="py-3.5 px-4 font-bold text-slate-900 flex items-center gap-2">
                  <div className="w-7 h-7 rounded-full bg-primary-50 text-primary-600 flex items-center justify-center font-bold text-xs">
                    📦
                  </div>
                  <div>
                    <span className="group-hover:text-primary-600 transition-colors">{s.tracking_number}</span>
                    <div className="text-[10px] text-slate-400 font-normal">📍 {s.current_location || 'En route'}</div>
                  </div>
                </td>
                <td className="py-3.5 px-4">
                  {getStatusBadge(s.status, s.delay_probability)}
                </td>
                <td className="py-3.5 px-4">
                  <div className="font-semibold text-slate-800">{s.origin} ➔ {s.destination}</div>
                </td>
                <td className="py-3.5 px-4">
                  <span className="font-medium text-slate-800">{s.carrier?.name || 'BlueDart'}</span>
                </td>
                <td className="py-3.5 px-4">
                  <div>{s.package_weight ? `${s.package_weight} kg` : '15 kg'}</div>
                  <div className="text-[11px] text-slate-400 font-medium">₹{Number(s.package_value || 50000).toLocaleString()}</div>
                </td>
                <td className="py-3.5 px-4">
                  <div className="flex items-center gap-2">
                    <div className="w-16 h-2 bg-slate-100 rounded-full overflow-hidden">
                      <div
                        className={`h-full ${
                          (s.delay_probability ?? 0) >= 0.7 ? 'bg-red-500' :
                          (s.delay_probability ?? 0) >= 0.3 ? 'bg-amber-500' : 'bg-emerald-500'
                        }`}
                        style={{ width: `${Math.round((s.delay_probability ?? 0.15) * 100)}%` }}
                      />
                    </div>
                    <span className="font-bold text-[11px]">
                      {Math.round((s.delay_probability ?? 0.15) * 100)}%
                    </span>
                  </div>
                </td>
                <td className="py-3.5 px-4 whitespace-nowrap text-xs text-slate-500">
                  {s.expected_delivery ? new Date(s.expected_delivery).toLocaleDateString() : 'Tomorrow'}
                </td>
                <td className="py-3.5 px-4 text-right whitespace-nowrap">
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onSelectAndSwitchToMap(s);
                    }}
                    className="text-xs font-semibold text-primary-600 hover:text-primary-700 bg-primary-50 hover:bg-primary-100 px-2.5 py-1.5 rounded-lg mr-2 transition-colors"
                  >
                    Track
                  </button>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onInjectDelay(s.tracking_number);
                    }}
                    className="text-xs font-semibold text-amber-600 hover:text-amber-700 bg-amber-50 hover:bg-amber-100 px-2.5 py-1.5 rounded-lg transition-colors"
                  >
                    ⚡ Anomaly
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
