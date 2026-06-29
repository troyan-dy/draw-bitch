"use client";

import { useCallback, useEffect, useRef } from "react";

import type { Segment } from "@/lib/types";

// Холст рисует входящие штрихи (координаты нормализованы 0..1) и, если canDraw,
// шлёт собственные сегменты по pointer-событиям.

const BG = "#ffffff";

export default function Canvas({
  strokes,
  canDraw,
  color,
  size,
  onSegment,
}: {
  strokes: Segment[];
  canDraw: boolean;
  color: string;
  size: number;
  onSegment: (seg: Segment) => void;
}) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const drawnRef = useRef(0); // сколько штрихов уже отрисовано
  const drawingRef = useRef(false);
  const lastRef = useRef<{ x: number; y: number } | null>(null);

  const drawSegment = useCallback((ctx: CanvasRenderingContext2D, seg: Segment) => {
    const { width, height } = ctx.canvas;
    ctx.strokeStyle = seg.color;
    ctx.lineWidth = seg.size;
    ctx.lineCap = "round";
    ctx.lineJoin = "round";
    ctx.beginPath();
    ctx.moveTo(seg.x0 * width, seg.y0 * height);
    ctx.lineTo(seg.x1 * width, seg.y1 * height);
    ctx.stroke();
  }, []);

  const redrawAll = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    ctx.fillStyle = BG;
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    for (const seg of strokes) drawSegment(ctx, seg);
    drawnRef.current = strokes.length;
  }, [strokes, drawSegment]);

  // Подгоняем буфер холста под физический размер контейнера (HiDPI).
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const resize = () => {
      const rect = canvas.getBoundingClientRect();
      const dpr = window.devicePixelRatio || 1;
      canvas.width = Math.max(1, Math.round(rect.width * dpr));
      canvas.height = Math.max(1, Math.round(rect.height * dpr));
      redrawAll();
    };
    resize();
    const ro = new ResizeObserver(resize);
    ro.observe(canvas);
    return () => ro.disconnect();
  }, [redrawAll]);

  // Инкрементальная дорисовка: если пришли новые штрихи — рисуем только их;
  // если массив укоротился (clear) — перерисовываем всё.
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    if (strokes.length < drawnRef.current) {
      redrawAll();
      return;
    }
    for (let i = drawnRef.current; i < strokes.length; i++) {
      drawSegment(ctx, strokes[i]);
    }
    drawnRef.current = strokes.length;
  }, [strokes, drawSegment, redrawAll]);

  function pointFromEvent(e: React.PointerEvent): { x: number; y: number } {
    const rect = e.currentTarget.getBoundingClientRect();
    return {
      x: (e.clientX - rect.left) / rect.width,
      y: (e.clientY - rect.top) / rect.height,
    };
  }

  function onPointerDown(e: React.PointerEvent) {
    if (!canDraw) return;
    e.currentTarget.setPointerCapture(e.pointerId);
    drawingRef.current = true;
    const p = pointFromEvent(e);
    lastRef.current = p;
    // Точка = нулевой сегмент, чтобы клик оставлял след.
    onSegment({ x0: p.x, y0: p.y, x1: p.x, y1: p.y, color, size });
  }

  function onPointerMove(e: React.PointerEvent) {
    if (!canDraw || !drawingRef.current || !lastRef.current) return;
    const p = pointFromEvent(e);
    const last = lastRef.current;
    onSegment({ x0: last.x, y0: last.y, x1: p.x, y1: p.y, color, size });
    lastRef.current = p;
  }

  function endStroke() {
    drawingRef.current = false;
    lastRef.current = null;
  }

  return (
    <canvas
      ref={canvasRef}
      onPointerDown={onPointerDown}
      onPointerMove={onPointerMove}
      onPointerUp={endStroke}
      onPointerLeave={endStroke}
      style={{ cursor: canDraw ? "crosshair" : "default" }}
    />
  );
}
