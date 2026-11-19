'use client';

import React, { useEffect, useRef } from 'react';
import L from 'leaflet';

interface Waypoint {
  name: string;
  lat: number;
  lng: number;
}

interface ShipmentItem {
  id: number;
  tracking_number: string;
  origin: string;
  destination: string;
  status: string;
  current_location?: string;
  current_latitude?: number;
  current_longitude?: number;
  delay_probability?: number;
  risk_level?: string;
  shipment_type?: string;
}

interface InteractiveMapProps {
  shipments: ShipmentItem[];
  selectedShipment: ShipmentItem | null;
  routesData: Record<string, Waypoint[]>;
  onSelectShipment: (s: ShipmentItem) => void;
}

export default function InteractiveMap({
  shipments,
  selectedShipment,
  routesData,
  onSelectShipment,
}: InteractiveMapProps) {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<L.Map | null>(null);
  const layerGroupRef = useRef<L.LayerGroup | null>(null);

  // Initialize Map Once
  useEffect(() => {
    if (!mapContainerRef.current) return;

    if (!mapInstanceRef.current) {
      const map = L.map(mapContainerRef.current, {
        center: [21.5, 79.0], // Center of India
        zoom: 5,
        zoomControl: false,
      });

      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
        maxZoom: 19,
      }).addTo(map);

      // Custom zoom control in bottom right
      L.control.zoom({ position: 'bottomright' }).addTo(map);

      mapInstanceRef.current = map;
      layerGroupRef.current = L.layerGroup().addTo(map);
    }

    return () => {
      // Map cleanup on unmount
      if (mapInstanceRef.current) {
        mapInstanceRef.current.remove();
        mapInstanceRef.current = null;
      }
    };
  }, []);

  // Update Markers & Polylines whenever shipments or selectedShipment change
  useEffect(() => {
    const map = mapInstanceRef.current;
    const layerGroup = layerGroupRef.current;
    if (!map || !layerGroup) return;

    layerGroup.clearLayers();

    // Helper to get route key
    const getWaypoints = (origin: string, destination: string): Waypoint[] => {
      const direct = `${origin}->${destination}`;
      if (routesData[direct]) return routesData[direct];
      const reverse = `${destination}->${origin}`;
      if (routesData[reverse]) return [...routesData[reverse]].reverse();
      return [];
    };

    // 1. Draw all other background routes (faint dashed)
    shipments.forEach((s) => {
      if (selectedShipment && s.id === selectedShipment.id) return;
      const wps = getWaypoints(s.origin, s.destination);
      if (wps.length >= 2) {
        const latlngs = wps.map((w) => [w.lat, w.lng] as [number, number]);
        const polyline = L.polyline(latlngs, {
          color: '#94A3B8',
          weight: 2.5,
          opacity: 0.5,
          dashArray: '4, 6',
        });
        polyline.on('click', () => onSelectShipment(s));
        layerGroup.addLayer(polyline);

        // Add subtle vehicle pin
        if (s.current_latitude && s.current_longitude) {
          const isDelayed = s.status === 'DELAYED' || s.risk_level === 'HIGH';
          const bgCol = isDelayed ? '#EF4444' : '#2563EB';
          const otherIcon = L.divIcon({
            className: 'custom-vehicle-icon',
            html: `
              <div style="background-color: ${bgCol}; width: 22px; height: 22px; border-radius: 9999px; display: flex; align-items: center; justify-content: center; box-shadow: 0 2px 6px rgba(0,0,0,0.25); border: 2px solid white; cursor: pointer;">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                  <rect x="1" y="3" width="15" height="13"></rect>
                  <polygon points="16 8 20 8 23 11 23 16 16 16 16 8"></polygon>
                  <circle cx="5.5" cy="18.5" r="2.5"></circle>
                  <circle cx="18.5" cy="18.5" r="2.5"></circle>
                </svg>
              </div>
            `,
            iconSize: [22, 22],
            iconAnchor: [11, 11],
          });
          const marker = L.marker([s.current_latitude, s.current_longitude], { icon: otherIcon });
          marker.bindTooltip(`<b>${s.tracking_number}</b><br/>${s.status}`, { direction: 'top', offset: [0, -10] });
          marker.on('click', () => onSelectShipment(s));
          layerGroup.addLayer(marker);
        }
      }
    });

    // 2. Highlight Selected Shipment Route & Markers
    if (selectedShipment) {
      const s = selectedShipment;
      const wps = getWaypoints(s.origin, s.destination);

      if (wps.length >= 2) {
        const isDelayed = s.status === 'DELAYED' || (s.delay_probability ?? 0) >= 0.7;

        // Draw normal and congested route segments (just like in the reference image!)
        if (isDelayed && wps.length >= 4) {
          // Congested middle segment
          const midStart = Math.max(1, Math.floor(wps.length / 3));
          const midEnd = Math.min(wps.length - 1, midStart + 2);

          const seg1 = wps.slice(0, midStart + 1).map((w) => [w.lat, w.lng] as [number, number]);
          const segCongested = wps.slice(midStart, midEnd + 1).map((w) => [w.lat, w.lng] as [number, number]);
          const seg2 = wps.slice(midEnd).map((w) => [w.lat, w.lng] as [number, number]);

          layerGroup.addLayer(L.polyline(seg1, { color: '#2563EB', weight: 4.5, opacity: 0.9 }));
          // RED Congestion line
          const redLine = L.polyline(segCongested, { color: '#EF4444', weight: 5.5, opacity: 1 });
          layerGroup.addLayer(redLine);
          layerGroup.addLayer(L.polyline(seg2, { color: '#2563EB', weight: 4.5, opacity: 0.9 }));

          // Floating Callout Badge "Traffic congestion" / "Monsoon Storm" (Mirrors Reference Screenshot!)
          const midPoint = wps[midStart + 1] || wps[midStart];
          const badgeIcon = L.divIcon({
            className: 'congestion-callout',
            html: `
              <div style="background-color: #DC2626; color: white; font-weight: 700; font-size: 11px; padding: 4px 10px; border-radius: 6px; box-shadow: 0 4px 12px rgba(220, 38, 38, 0.4); display: flex; align-items: center; gap: 5px; white-space: nowrap; border: 1.5px solid white;">
                <span style="display: inline-block; width: 6px; height: 6px; border-radius: 9999px; background-color: #FEF08A; animation: ping 1s cubic-bezier(0, 0, 0.2, 1) infinite;"></span>
                ${s.status === 'DELAYED' ? 'Traffic congestion' : 'Severe Weather Alert'}
              </div>
            `,
            iconSize: [120, 26],
            iconAnchor: [60, 36],
          });
          layerGroup.addLayer(L.marker([midPoint.lat, midPoint.lng], { icon: badgeIcon }));
        } else {
          // Standard Clean Blue Line
          const latlngs = wps.map((w) => [w.lat, w.lng] as [number, number]);
          layerGroup.addLayer(L.polyline(latlngs, { color: '#2563EB', weight: 4.5, opacity: 0.9 }));
        }

        // Origin Marker (Pin A)
        const originIcon = L.divIcon({
          className: 'origin-marker',
          html: `
            <div style="background: white; border: 3px solid #2563EB; width: 24px; height: 24px; border-radius: 9999px; display: flex; align-items: center; justify-content: center; box-shadow: 0 3px 8px rgba(0,0,0,0.25);">
              <div style="background: #2563EB; width: 8px; height: 8px; border-radius: 9999px;"></div>
            </div>
          `,
          iconSize: [24, 24],
          iconAnchor: [12, 12],
        });
        const originMarker = L.marker([wps[0].lat, wps[0].lng], { icon: originIcon });
        originMarker.bindTooltip(`<b>Origin: ${wps[0].name}</b>`, { permanent: false, direction: 'top' });
        layerGroup.addLayer(originMarker);

        // Destination Marker (Pin B)
        const lastWp = wps[wps.length - 1];
        const destIcon = L.divIcon({
          className: 'dest-marker',
          html: `
            <div style="background: #0F172A; border: 2px solid white; width: 24px; height: 24px; border-radius: 6px; display: flex; align-items: center; justify-content: center; box-shadow: 0 3px 8px rgba(0,0,0,0.35);">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="3">
                <rect x="3" y="3" width="18" height="18" rx="2"/>
              </svg>
            </div>
          `,
          iconSize: [24, 24],
          iconAnchor: [12, 12],
        });
        const destMarker = L.marker([lastWp.lat, lastWp.lng], { icon: destIcon });
        destMarker.bindTooltip(`<b>Destination: ${lastWp.name}</b>`, { permanent: false, direction: 'top' });
        layerGroup.addLayer(destMarker);

        // Numbered Waypoint Badges (1, 2, 3...) (Just like in the reference image!)
        wps.slice(1, -1).forEach((wp, idx) => {
          const numIcon = L.divIcon({
            className: 'wp-num-icon',
            html: `
              <div style="background: white; border: 2px solid #DC2626; color: #DC2626; font-size: 10px; font-weight: 800; width: 18px; height: 18px; border-radius: 9999px; display: flex; align-items: center; justify-content: center; box-shadow: 0 2px 5px rgba(0,0,0,0.2);">
                ${idx + 1}
              </div>
            `,
            iconSize: [18, 18],
            iconAnchor: [9, 9],
          });
          const wpMarker = L.marker([wp.lat, wp.lng], { icon: numIcon });
          wpMarker.bindTooltip(wp.name, { direction: 'top' });
          layerGroup.addLayer(wpMarker);
        });

        // Current Animated Moving Vehicle Pin (Exact replica of blue directional arrow + pulsing glow!)
        const curLat = s.current_latitude ?? wps[0].lat;
        const curLng = s.current_longitude ?? wps[0].lng;

        const vehiclePulseIcon = L.divIcon({
          className: 'active-truck-icon',
          html: `
            <div style="position: relative; width: 44px; height: 44px; display: flex; align-items: center; justify-content: center;">
              <!-- Outer translucent aura -->
              <div style="position: absolute; width: 44px; height: 44px; border-radius: 9999px; background: rgba(37, 99, 235, 0.22); border: 1.5px solid rgba(37, 99, 235, 0.4);" class="vehicle-pulse-marker"></div>
              <!-- Inner solid badge with blue arrow / play triangle -->
              <div style="position: relative; width: 28px; height: 28px; border-radius: 9999px; background: #2563EB; border: 2.5px solid white; display: flex; align-items: center; justify-content: center; box-shadow: 0 4px 10px rgba(37, 99, 235, 0.5);">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="white" stroke="white" stroke-width="2">
                  <polygon points="6 4 20 12 6 20 6 4"></polygon>
                </svg>
              </div>
            </div>
          `,
          iconSize: [44, 44],
          iconAnchor: [22, 22],
        });

        const vMarker = L.marker([curLat, curLng], { icon: vehiclePulseIcon, zIndexOffset: 1000 });
        vMarker.bindPopup(`
          <div style="padding: 4px; font-family: sans-serif;">
            <div style="font-size: 11px; color: #64748B; font-weight: 600;">ACTIVE SHIPMENT</div>
            <div style="font-size: 14px; font-weight: 700; color: #0F172A; margin: 2px 0;">${s.tracking_number}</div>
            <div style="display: flex; gap: 6px; margin: 6px 0;">
              <span style="background: #EFF6FF; color: #2563EB; font-size: 11px; padding: 2px 8px; border-radius: 9999px; font-weight: 600;">${s.status}</span>
              <span style="background: #F1F5F9; color: #475569; font-size: 11px; padding: 2px 8px; border-radius: 9999px;">${s.origin} ➔ ${s.destination}</span>
            </div>
            <div style="font-size: 11px; color: #475569; margin-top: 4px;">📍 ${s.current_location || 'En route'}</div>
          </div>
        `);
        layerGroup.addLayer(vMarker);
      }
    }
  }, [shipments, selectedShipment, routesData, onSelectShipment]);

  return (
    <div className="relative w-full h-full min-h-[480px] bg-slate-100 rounded-xl overflow-hidden border border-slate-200 shadow-sm">
      <div ref={mapContainerRef} className="w-full h-full" />

      {/* Recenter / Focus button */}
      <div className="absolute top-4 right-4 z-[500] flex gap-2">
        <button
          onClick={() => {
            if (mapInstanceRef.current && selectedShipment && selectedShipment.current_latitude && selectedShipment.current_longitude) {
              mapInstanceRef.current.flyTo([selectedShipment.current_latitude, selectedShipment.current_longitude], 7, { duration: 1.2 });
            } else if (mapInstanceRef.current) {
              mapInstanceRef.current.flyTo([21.5, 79.0], 5, { duration: 1.2 });
            }
          }}
          className="bg-white/95 hover:bg-white text-slate-700 text-xs font-semibold px-3 py-1.5 rounded-lg shadow-md border border-slate-200/80 backdrop-blur-sm flex items-center gap-1.5 transition-all"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="12" cy="12" r="10" />
            <circle cx="12" cy="12" r="3" />
          </svg>
          Focus Vehicle
        </button>
      </div>

      {/* Simulated telematics watermark / status badge */}
      <div className="absolute bottom-3 left-3 z-[500]">
        <div className="bg-slate-900/85 text-white backdrop-blur-md px-3 py-1.5 rounded-lg text-xs font-medium border border-slate-700/60 shadow-lg flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
          <span>⚡ Simulated Telematics Stream • 4s Ticks</span>
        </div>
      </div>
    </div>
  );
}
