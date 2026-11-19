'use client';

import React from 'react';

interface ShipmentItem {
  distance_km?: number;
  package_weight?: number;
  package_value?: number;
  delay_probability?: number;
  risk_level?: string;
  status?: string;
}

interface ShipmentSummaryCardsProps {
  shipment: ShipmentItem | null;
  allShipments?: ShipmentItem[];
}

export default function ShipmentSummaryCards({ shipment, allShipments = [] }: ShipmentSummaryCardsProps) {
  // Aggregate stats from all shipments (not hardcoded)
  const shipmentsList = allShipments.length > 0 ? allShipments : (shipment ? [shipment] : []);

  const totalDistance = shipmentsList.reduce((sum, s) => sum + (s.distance_km || 0), 0);
  const totalWeight = shipmentsList.reduce((sum, s) => sum + (s.package_weight || 0), 0);
  const totalValue = shipmentsList.reduce((sum, s) => sum + (Number(s.package_value) || 0), 0);
  const highRiskCount = shipmentsList.filter(
    (s) => s.status === 'DELAYED' || (s.delay_probability ?? 0) >= 0.7
  ).length;

  const hasData = shipmentsList.length > 0;
  const distance = hasData ? `${totalDistance.toLocaleString()} km` : '0 km';
  const weight = hasData ? `${totalWeight.toLocaleString()} kg` : '0 kg';
  const value = hasData ? `₹${totalValue.toLocaleString()}` : '₹0';

  return (
    <div className="grid grid-cols-1 sm:grid-cols-3 gap-3.5 mb-3.5">
      {/* 1. Total Distance Card */}
      <div className="bg-white rounded-xl p-4 sm:p-5 border border-slate-200/90 shadow-sm flex flex-col justify-between">
        <div className="flex items-center gap-2 mb-2">
          <div className="w-7 h-7 rounded-full bg-emerald-50 text-emerald-600 flex items-center justify-center">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1z"></path>
              <line x1="4" y1="22" x2="4" y2="15"></line>
            </svg>
          </div>
          <span className="text-xs font-semibold text-slate-500 tracking-tight">Total distance</span>
        </div>

        <div>
          <div className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
            {distance}
          </div>
          <div className="text-[11px] font-semibold text-slate-500 mt-1 flex items-center gap-1">
            <span>📦</span>
            <span>Across {shipmentsList.length} shipment{shipmentsList.length !== 1 ? 's' : ''}</span>
          </div>
        </div>
      </div>

      {/* 2. Total Weight Card */}
      <div className="bg-white rounded-xl p-4 sm:p-5 border border-slate-200/90 shadow-sm flex flex-col justify-between">
        <div className="flex items-center gap-2 mb-2">
          <div className="w-7 h-7 rounded-full bg-rose-50 text-rose-600 flex items-center justify-center">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="9"/>
              <path d="m16 8-8 8"/>
              <path d="m8 8 8 8"/>
            </svg>
          </div>
          <span className="text-xs font-semibold text-slate-500 tracking-tight">Total weight</span>
        </div>

        <div>
          <div className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
            {weight}
          </div>
          <div className="text-[11px] font-semibold text-emerald-600 mt-1 flex items-center gap-1">
            <span>✓</span>
            <span>Calculated from actual records</span>
          </div>
        </div>
      </div>

      {/* 3. Total Value Card */}
      <div className="bg-white rounded-xl p-4 sm:p-5 border border-slate-200/90 shadow-sm flex flex-col justify-between">
        <div className="flex items-center gap-2 mb-2">
          <div className="w-7 h-7 rounded-full bg-sky-50 text-primary-600 flex items-center justify-center font-bold text-xs">
            ₹
          </div>
          <span className="text-xs font-semibold text-slate-500 tracking-tight">Total value</span>
        </div>

        <div>
          <div className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
            {value}
          </div>
          <div className={`text-[11px] font-semibold mt-1 flex items-center gap-1 ${
            highRiskCount > 0 ? 'text-amber-600' : 'text-slate-500'
          }`}>
            <span>→</span>
            <span>
              {highRiskCount > 0
                ? `${highRiskCount} shipment${highRiskCount !== 1 ? 's' : ''} at high delay risk`
                : 'All shipments on schedule'}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
