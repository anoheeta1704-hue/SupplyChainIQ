'use client';

import React, { useState } from 'react';
import { API_BASE } from '@/lib/config';

interface AddShipmentModalProps {
  isOpen: boolean;
  onClose: () => void;
  onCreated: (newShipment: any) => void;
}

export default function AddShipmentModal({ isOpen, onClose, onCreated }: AddShipmentModalProps) {
  const [origin, setOrigin] = useState('Bengaluru');
  const [destination, setDestination] = useState('Kolkata');
  const [carrierCode, setCarrierCode] = useState('BD');
  const [shipmentType, setShipmentType] = useState('EXPRESS');
  const [weight, setWeight] = useState('25.0');
  const [value, setValue] = useState('150000');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (origin === destination) {
      setError('Origin and destination cannot be the same');
      return;
    }
    setError('');
    setLoading(true);

    try {
      const carrierMap: Record<string, number> = { BD: 2, DLV: 1, ECOM: 3, XB: 4 };
      const expectedDate = new Date();
      expectedDate.setHours(expectedDate.getHours() + 48);

      const res = await fetch(`${API_BASE}/api/shipments`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          origin,
          destination,
          carrier_id: carrierMap[carrierCode] || 1,
          shipment_type: shipmentType,
          package_weight: parseFloat(weight) || 10.0,
          package_value: parseFloat(value) || 50000.0,
          expected_delivery: expectedDate.toISOString(),
        }),
      });

      if (!res.ok) {
        throw new Error(`Failed to create shipment: ${res.statusText}`);
      }

      const created = await res.json();
      onCreated(created);
      onClose();
    } catch (err: any) {
      setError(err.message || 'Error creating shipment');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-[1000] flex items-center justify-center p-4 bg-slate-950/60 backdrop-blur-sm animate-fade-in">
      <div className="bg-white rounded-2xl shadow-2xl max-w-lg w-full overflow-hidden border border-slate-200">
        {/* Header */}
        <div className="bg-navy-900 px-6 py-4 flex items-center justify-between text-white border-b border-slate-800">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-primary-600 flex items-center justify-center font-bold">
              📦
            </div>
            <div>
              <h2 className="text-base font-bold">Create New Shipment</h2>
              <p className="text-xs text-slate-400">Add order into operational database</p>
            </div>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-white p-1">
            ✕
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="p-6 space-y-4 text-xs sm:text-sm">
          {error && (
            <div className="bg-red-50 text-red-600 p-3 rounded-lg text-xs font-semibold">
              {error}
            </div>
          )}

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block font-semibold text-slate-700 mb-1">Origin City</label>
              <select
                value={origin}
                onChange={(e) => setOrigin(e.target.value)}
                className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-slate-900 font-medium focus:outline-none focus:ring-2 focus:ring-primary-500"
              >
                <option value="Bengaluru">Bengaluru</option>
                <option value="Mumbai">Mumbai</option>
                <option value="Delhi">Delhi</option>
                <option value="Chennai">Chennai</option>
                <option value="Kolkata">Kolkata</option>
                <option value="Hyderabad">Hyderabad</option>
                <option value="Pune">Pune</option>
              </select>
            </div>

            <div>
              <label className="block font-semibold text-slate-700 mb-1">Destination City</label>
              <select
                value={destination}
                onChange={(e) => setDestination(e.target.value)}
                className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-slate-900 font-medium focus:outline-none focus:ring-2 focus:ring-primary-500"
              >
                <option value="Kolkata">Kolkata</option>
                <option value="Delhi">Delhi</option>
                <option value="Bengaluru">Bengaluru</option>
                <option value="Hyderabad">Hyderabad</option>
                <option value="Mumbai">Mumbai</option>
                <option value="Ahmedabad">Ahmedabad</option>
                <option value="Guwahati">Guwahati</option>
              </select>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block font-semibold text-slate-700 mb-1">Carrier Partner</label>
              <select
                value={carrierCode}
                onChange={(e) => setCarrierCode(e.target.value)}
                className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-slate-900 font-medium focus:outline-none focus:ring-2 focus:ring-primary-500"
              >
                <option value="BD">BlueDart (Air Priority)</option>
                <option value="DLV">Delhivery (Express)</option>
                <option value="ECOM">Ecom Express (Standard)</option>
                <option value="XB">XpressBees (Freight)</option>
              </select>
            </div>

            <div>
              <label className="block font-semibold text-slate-700 mb-1">Service Type</label>
              <select
                value={shipmentType}
                onChange={(e) => setShipmentType(e.target.value)}
                className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-slate-900 font-medium focus:outline-none focus:ring-2 focus:ring-primary-500"
              >
                <option value="EXPRESS">EXPRESS</option>
                <option value="STANDARD">STANDARD</option>
                <option value="FRAGILE">FRAGILE</option>
                <option value="BULK">BULK CARGO</option>
              </select>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block font-semibold text-slate-700 mb-1">Weight (kg)</label>
              <input
                type="number"
                step="0.1"
                value={weight}
                onChange={(e) => setWeight(e.target.value)}
                className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-slate-900 font-medium focus:outline-none focus:ring-2 focus:ring-primary-500"
                required
              />
            </div>

            <div>
              <label className="block font-semibold text-slate-700 mb-1">Declared Value (₹)</label>
              <input
                type="number"
                value={value}
                onChange={(e) => setValue(e.target.value)}
                className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-slate-900 font-medium focus:outline-none focus:ring-2 focus:ring-primary-500"
                required
              />
            </div>
          </div>

          <div className="pt-3 flex items-center justify-end gap-3 border-t border-slate-100">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-xl text-slate-600 hover:bg-slate-100 font-medium transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="bg-primary-600 hover:bg-primary-500 text-white font-bold px-5 py-2 rounded-xl shadow-md transition-all flex items-center gap-2"
            >
              {loading ? 'Creating...' : 'Save & Track'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
