'use client';

import React from 'react';

interface ShipmentCardProps {
  shipment: {
    id: number;
    tracking_number: string;
    origin: string;
    destination: string;
    status: string;
    shipment_type?: string;
    carrier?: { name: string };
    created_at?: string;
    expected_delivery?: string;
    actual_delivery?: string;
    delay_probability?: number;
    risk_level?: string;
    package_weight?: number;
    package_value?: number;
  };
  isSelected: boolean;
  onSelect: () => void;
}

export default function ShipmentCard({ shipment, isSelected, onSelect }: ShipmentCardProps) {
  const isPlane = shipment.shipment_type === 'EXPRESS' || shipment.carrier?.name === 'BlueDart';
  const isDelayed = shipment.status === 'DELAYED' || (shipment.delay_probability ?? 0) >= 0.7;

  // Format dates nicely
  const formatDate = (dateStr?: string) => {
    if (!dateStr) return 'Pending schedule';
    try {
      const d = new Date(dateStr);
      return `${String(d.getMonth() + 1).padStart(2, '0')}/${String(d.getDate()).padStart(2, '0')}/${d.getFullYear()} ${d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;
    } catch {
      return dateStr;
    }
  };

  const statusLabel = () => {
    switch (shipment.status) {
      case 'IN_TRANSIT':
        return 'In transit';
      case 'DELAYED':
        return 'Delayed';
      case 'AT_WAREHOUSE':
        return 'Stationary';
      case 'OUT_FOR_DELIVERY':
        return 'Out for delivery';
      case 'DELIVERED':
        return 'Delivered';
      case 'CREATED':
        return 'Manifested';
      default:
        return shipment.status;
    }
  };

  const statusBadgeStyle = () => {
    if (isDelayed) {
      return 'bg-red-50 text-red-600 border border-red-200/80';
    }
    switch (shipment.status) {
      case 'IN_TRANSIT':
        return 'bg-sky-50 text-primary-600 border border-primary-200/60';
      case 'DELIVERED':
        return 'bg-emerald-50 text-emerald-600 border border-emerald-200/60';
      case 'AT_WAREHOUSE':
        return 'bg-slate-100 text-slate-700 border border-slate-200';
      default:
        return 'bg-blue-50 text-blue-600 border border-blue-200/60';
    }
  };

  return (
    <div
      onClick={onSelect}
      className={`bg-white rounded-xl p-4 sm:p-5 transition-all cursor-pointer border ${
        isSelected
          ? 'border-primary-500 shadow-md ring-2 ring-primary-500/10'
          : 'border-slate-200/90 hover:border-slate-300 hover:shadow-sm'
      }`}
    >
      {/* Top Header Row */}
      <div className="flex items-center justify-between gap-2 mb-3.5">
        <div className="flex items-center gap-3">
          {/* Vehicle Icon Circle */}
          <div className="w-10 h-10 rounded-full bg-primary-600 flex items-center justify-center text-white shadow-sm flex-shrink-0">
            {isPlane ? (
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M17.8 19.2 16 11l3.5-3.5C21 6 21.5 4 21 3c-1-.5-3 0-4.5 1.5L13 8 4.8 6.2c-.5-.1-.9.1-1.1.5l-.3.5c-.2.5-.1 1 .3 1.3L9 12l-2 3H4l-1 1 3 2 2 3 1-1v-3l3-2 3.5 5.3c.3.4.8.5 1.3.3l.5-.2c.4-.3.6-.7.5-1.2z"/>
              </svg>
            ) : (
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                <rect x="1" y="3" width="15" height="13"></rect>
                <polygon points="16 8 20 8 23 11 23 16 16 16 16 8"></polygon>
                <circle cx="5.5" cy="18.5" r="2.5"></circle>
                <circle cx="18.5" cy="18.5" r="2.5"></circle>
              </svg>
            )}
          </div>

          <div>
            <div className="text-[11px] font-medium text-slate-400 uppercase tracking-wider">
              Shipping ID
            </div>
            <div className="text-sm font-bold text-slate-900 tracking-tight">
              {shipment.tracking_number}
            </div>
          </div>
        </div>

        {/* Right Badge & Options */}
        <div className="flex items-center gap-2">
          <span className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold ${statusBadgeStyle()}`}>
            {isPlane ? '✈' : '🚚'} {statusLabel()}
          </span>

          <button className="text-slate-400 hover:text-slate-600 p-1">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
              <circle cx="12" cy="5" r="2"/>
              <circle cx="12" cy="12" r="2"/>
              <circle cx="12" cy="19" r="2"/>
            </svg>
          </button>
        </div>
      </div>

      {/* Origin & Destination Timeline Track (Matches Reference!) */}
      <div className="relative pl-6 space-y-3.5 text-xs">
        {/* Vertical connecting line */}
        <div className="absolute left-2 top-2 bottom-2 w-0.5 bg-slate-200"></div>

        {/* Origin Row */}
        <div className="relative flex items-baseline justify-between gap-2">
          {/* Blue Dot */}
          <span className="absolute -left-6 top-1 w-2.5 h-2.5 rounded-full bg-primary-600 ring-2 ring-white"></span>
          <span className="font-semibold text-slate-800">{shipment.origin}</span>
          <span className="text-[11px] text-slate-400 font-medium whitespace-nowrap">
            {formatDate(shipment.created_at)}
          </span>
        </div>

        {/* Destination Row */}
        <div className="relative flex items-baseline justify-between gap-2">
          {/* Dark Square */}
          <span className="absolute -left-6 top-1 w-2.5 h-2.5 rounded-sm bg-slate-900 ring-2 ring-white"></span>
          <span className="font-semibold text-slate-800">{shipment.destination}</span>
          <span className="text-[11px] text-slate-400 font-medium whitespace-nowrap">
            {formatDate(shipment.expected_delivery)}
          </span>
        </div>
      </div>
    </div>
  );
}
