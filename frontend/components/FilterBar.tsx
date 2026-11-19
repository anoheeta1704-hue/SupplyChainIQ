'use client';

import React from 'react';

interface FilterBarProps {
  search: string;
  onSearchChange: (val: string) => void;
  statusFilter: string;
  onStatusFilterChange: (val: string) => void;
  carrierFilter: string;
  onCarrierFilterChange: (val: string) => void;
  riskFilter: string;
  onRiskFilterChange: (val: string) => void;
  statusCounts: { inTransit: number; delayed: number; total: number };
}

export default function FilterBar({
  search,
  onSearchChange,
  statusFilter,
  onStatusFilterChange,
  carrierFilter,
  onCarrierFilterChange,
  riskFilter,
  onRiskFilterChange,
  statusCounts,
}: FilterBarProps) {
  return (
    <div className="bg-navy-900 px-4 sm:px-6 lg:px-8 py-3.5 border-b border-slate-800/60">
      <div className="max-w-[1720px] mx-auto flex flex-col md:flex-row items-stretch md:items-center justify-between gap-3">
        {/* Search input with rounded pill design */}
        <div className="relative flex-1 max-w-xl">
          <input
            type="text"
            value={search}
            onChange={(e) => onSearchChange(e.target.value)}
            placeholder="Search by ID, status, departure, arrival..."
            className="w-full bg-[#111A35] text-slate-100 placeholder-slate-400 text-xs sm:text-sm pl-4 pr-10 py-2.5 rounded-full border border-slate-700/60 focus:outline-none focus:ring-2 focus:ring-primary-500/50 focus:border-primary-500 transition-all shadow-inner"
          />
          <div className="absolute right-3.5 top-1/2 -translate-y-1/2 pointer-events-none text-slate-400">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="11" cy="11" r="8"></circle>
              <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
            </svg>
          </div>
        </div>

        {/* Filter Pills Matching Reference */}
        <div className="flex flex-wrap items-center gap-2 text-xs">
          {/* Status Filter */}
          <div className="relative inline-block">
            <select
              value={statusFilter}
              onChange={(e) => onStatusFilterChange(e.target.value)}
              className="appearance-none bg-[#111A35] text-slate-200 border border-slate-700/70 hover:border-slate-600 px-3.5 py-2 pr-7 rounded-full font-medium cursor-pointer focus:outline-none focus:ring-1 focus:ring-primary-500 transition-colors"
            >
              <option value="ALL">Status: All ({statusCounts.total})</option>
              <option value="IN_TRANSIT">In transit ({statusCounts.inTransit})</option>
              <option value="DELAYED">Delayed ({statusCounts.delayed})</option>
              <option value="OUT_FOR_DELIVERY">Out for Delivery</option>
              <option value="AT_WAREHOUSE">At Warehouse</option>
              <option value="DELIVERED">Delivered</option>
              <option value="CREATED">Created</option>
            </select>
            <div className="pointer-events-none absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><polyline points="6 9 12 15 18 9"/></svg>
            </div>
          </div>

          {/* Carrier Filter */}
          <div className="relative inline-block">
            <select
              value={carrierFilter}
              onChange={(e) => onCarrierFilterChange(e.target.value)}
              className="appearance-none bg-[#111A35] text-slate-200 border border-slate-700/70 hover:border-slate-600 px-3.5 py-2 pr-7 rounded-full font-medium cursor-pointer focus:outline-none focus:ring-1 focus:ring-primary-500 transition-colors"
            >
              <option value="ALL">Carrier: All (4)</option>
              <option value="BlueDart">BlueDart</option>
              <option value="Delhivery">Delhivery</option>
              <option value="Ecom Express">Ecom Express</option>
              <option value="XpressBees">XpressBees</option>
            </select>
            <div className="pointer-events-none absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><polyline points="6 9 12 15 18 9"/></svg>
            </div>
          </div>

          {/* Value Filter */}
          <div className="relative inline-block">
            <button className="bg-[#111A35] text-slate-200 border border-slate-700/70 hover:border-slate-600 px-3.5 py-2 rounded-full font-medium flex items-center gap-1.5 transition-colors">
              <span>Total value: &gt; ₹25k</span>
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><polyline points="6 9 12 15 18 9"/></svg>
            </button>
          </div>

          {/* Delay Risk Filter */}
          <div className="relative inline-block">
            <select
              value={riskFilter}
              onChange={(e) => onRiskFilterChange(e.target.value)}
              className="appearance-none bg-[#111A35] text-slate-200 border border-slate-700/70 hover:border-slate-600 px-3.5 py-2 pr-7 rounded-full font-medium cursor-pointer focus:outline-none focus:ring-1 focus:ring-primary-500 transition-colors"
            >
              <option value="ALL">Risk: All</option>
              <option value="HIGH">High Risk ⚠️</option>
              <option value="MEDIUM">Medium Risk</option>
              <option value="LOW">Low Risk</option>
            </select>
            <div className="pointer-events-none absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><polyline points="6 9 12 15 18 9"/></svg>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
