"use client";

// Минимальная панель рисования: палитра, размеры кисти, ластик, очистка.

export const PALETTE = [
  "#000000",
  "#ffffff",
  "#ff5c7c",
  "#ffb454",
  "#ffe34d",
  "#44d07b",
  "#4db5ff",
  "#7c5cff",
];

export const SIZES = [4, 10, 20];
const ERASER = "#ffffff";

export default function Toolbar({
  color,
  size,
  onColor,
  onSize,
  onClear,
}: {
  color: string;
  size: number;
  onColor: (c: string) => void;
  onSize: (s: number) => void;
  onClear: () => void;
}) {
  const isEraser = color === ERASER;
  return (
    <div className="card toolbar">
      <div className="swatches">
        {PALETTE.map((c) => (
          <button
            key={c}
            className={`swatch ${color === c ? "active" : ""}`}
            style={{ background: c, borderColor: c === "#ffffff" ? "#ccc" : undefined }}
            onClick={() => onColor(c)}
            aria-label={`цвет ${c}`}
          />
        ))}
      </div>

      <div className="sizes">
        {SIZES.map((s) => (
          <button
            key={s}
            className={`size-btn ${size === s && !isEraser ? "active" : ""}`}
            onClick={() => onSize(s)}
            aria-label={`кисть ${s}`}
          >
            <span className="size-dot" style={{ width: s, height: s }} />
          </button>
        ))}
      </div>

      <button className={isEraser ? "active" : ""} onClick={() => onColor(ERASER)}>
        Ластик
      </button>
      <button onClick={onClear}>Очистить</button>
    </div>
  );
}
