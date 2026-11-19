'use client';

import React from 'react';
import Link from 'next/link';

interface TitleBarProps {
  viewMode: 'map' | 'list';
  onViewModeChange: (mode: 'map' | 'list') => void;
  onOpenAddModal: () => void;
  onOpenAnomalyModal: () => void;
  isSimRunning: boolean;
  simSpeed: number;
  onToggleSim: () => void;
  onStepSim: () => void;
  onChangeSpeed: (spd: number) => void;
  onResetSim: () => void;
  onRefresh?: () => void;
  isRefreshing?: boolean;
}

export default function TitleBar({
  viewMode,
  onViewModeChange,
  onOpenAddModal,
  onOpenAnomalyModal,
  isSimRunning,
  simSpeed,
  onToggleSim,
  onStepSim,
  onChangeSpeed,
  onResetSim,
  onRefresh,
  isRefreshing = false,
}: TitleBarProps) {
  return (
    <div className="bg-navy-900 px-4 sm:px-6 lg:px-8 py-4 border-b border-slate-800/80">
      <div className="max-w-[1720px] mx-auto flex flex-col lg:flex-row lg:items-center justify-between gap-4">
        {/* Title */}
        <div className="flex items-center gap-4">
          <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
            Shipment Tracking
          </h1>

          {/* Simulator Status Badge */}
          <div className="hidden sm:flex items-center gap-2 bg-[#121E3E] border border-slate-700/60 px-3 py-1 rounded-full text-xs text-slate-300">
            <span className={`w-2 h-2 rounded-full ${isSimRunning ? 'bg-emerald-400 animate-pulse' : 'bg-amber-400'}`} />
            <span>Sim: {isSimRunning ? `Running (${simSpeed}x)` : 'Paused'}</span>
          </div>
        </div>

        {/* Controls: View Switcher, Simulation Toolbar, and Add Shipment */}
        <div className="flex flex-wrap items-center gap-3">
          {/* Simulation Toolbar */}
          <div className="flex items-center gap-1.5 bg-[#111A35] border border-slate-700/70 p-1 rounded-xl">
            {/* Play/Pause */}
            <button
              onClick={onToggleSim}
              title={isSimRunning ? 'Pause Simulator' : 'Resume Simulator'}
              className={`px-2.5 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-all ${
                isSimRunning
                  ? 'bg-amber-500/20 text-amber-300 hover:bg-amber-500/30'
                  : 'bg-emerald-500/20 text-emerald-300 hover:bg-emerald-500/30'
              }`}
            >
              {isSimRunning ? (
                <>
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor"><rect x="6" y="4" width="4" height="16"/><rect x="14" y="4" width="4" height="16"/></svg>
                  <span>Pause</span>
                </>
              ) : (
                <>
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor"><polygon points="5 3 19 12 5 21 5 3"/></svg>
                  <span>Play</span>
                </>
              )}
            </button>

            {/* Step 1 tick */}
            <button
              onClick={onStepSim}
              title="Advance 1 Simulation Tick"
              className="px-2 py-1.5 rounded-lg text-xs text-slate-300 hover:text-white hover:bg-slate-800 transition-colors"
            >
              Step
            </button>

            {/* Speed Toggle */}
            <button
              onClick={() => onChangeSpeed(simSpeed === 1 ? 2 : simSpeed === 2 ? 5 : 1)}
              title="Change Speed Multiplier"
              className="px-2 py-1.5 rounded-lg text-xs font-semibold text-primary-400 hover:bg-slate-800 transition-colors"
            >
              {simSpeed}x
            </button>

            {/* Reset */}
            <button
              onClick={onResetSim}
              title="Reset Shipments to Initial Positions"
              className="px-2 py-1.5 rounded-lg text-xs text-slate-400 hover:text-red-300 hover:bg-red-500/10 transition-colors"
            >
              Reset
            </button>

            {/* Refresh */}
            {onRefresh && (
              <button
                onClick={onRefresh}
                disabled={isRefreshing}
                title="Fetch Fresh Records & Telematics from Database"
                className="px-2 py-1.5 rounded-lg text-xs text-slate-300 hover:text-white hover:bg-slate-800 transition-colors flex items-center gap-1 disabled:opacity-50"
              >
                <span className={isRefreshing ? "inline-block animate-spin" : ""}>↻</span>
                <span>{isRefreshing ? "Refreshing..." : "Refresh"}</span>
              </button>
            )}

            {/* Inject Anomaly */}
            <button
              onClick={onOpenAnomalyModal}
              title="Inject Weather or Traffic Anomaly"
              className="px-2.5 py-1.5 rounded-lg text-xs font-medium text-amber-400 hover:bg-amber-500/20 transition-colors flex items-center gap-1"
            >
              <span>⚡ Anomaly</span>
            </button>
          </div>

          {/* Map view / List view Pill Switcher (Matches Reference!) */}
          <div className="bg-[#111A35] border border-slate-700/70 p-1 rounded-xl flex items-center">
            <button
              onClick={() => onViewModeChange('map')}
              className={`px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                viewMode === 'map'
                  ? 'bg-slate-700/90 text-white shadow-sm'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              Map view
            </button>
            <button
              onClick={() => onViewModeChange('list')}
              className={`px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                viewMode === 'list'
                  ? 'bg-slate-700/90 text-white shadow-sm'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              List view
            </button>
            <Link
              href="/analytics"
              title="View Logistics Analytics & SLAs"
              className="px-3 py-1.5 rounded-lg text-xs font-semibold text-slate-400 hover:text-white hover:bg-slate-800 transition-colors flex items-center gap-1.5"
            >
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <line x1="18" y1="20" x2="18" y2="10"></line>
                <line x1="12" y1="20" x2="12" y2="4"></line>
                <line x1="6" y1="20" x2="6" y2="14"></line>
              </svg>
              <span>Analytics</span>
            </Link>
          </div>

          {/* + Add shipping Primary Button (Matches Reference!) */}
          <button
            onClick={onOpenAddModal}
            className="bg-primary-600 hover:bg-primary-500 text-white font-semibold text-xs sm:text-sm px-4 py-2 rounded-xl shadow-md shadow-primary-600/30 flex items-center gap-2 transition-all hover:scale-[1.02] active:scale-[0.98]"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <line x1="12" y1="5" x2="12" y2="19"></line>
              <line x1="5" y1="12" x2="19" y2="12"></line>
            </svg>
            <span>Add shipping</span>
          </button>
        </div>
      </div>
    </div>
  );
}
