"use client";

import { useState, useRef, useEffect, useCallback } from "react";

interface Props {
  nodeIds: string[];
  onSelect: (nodeId: string) => void;
  onClear: () => void;
}

export default function SearchBar({ nodeIds, onSelect, onClear }: Props) {
  const [query, setQuery] = useState("");
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [open, setOpen] = useState(false);
  const [activeIdx, setActiveIdx] = useState(-1);
  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLUListElement>(null);

  const handleChange = useCallback(
    (val: string) => {
      setQuery(val);
      setActiveIdx(-1);
      if (val.length < 2) {
        setSuggestions([]);
        setOpen(false);
        return;
      }
      const q = val.toLowerCase();
      const matches = nodeIds
        .filter((id) => id.toLowerCase().includes(q))
        .slice(0, 10);
      setSuggestions(matches);
      setOpen(matches.length > 0);
    },
    [nodeIds]
  );

  const handleSelect = useCallback(
    (nodeId: string) => {
      setQuery(nodeId);
      setSuggestions([]);
      setOpen(false);
      onSelect(nodeId);
    },
    [onSelect]
  );

  const handleClear = () => {
    setQuery("");
    setSuggestions([]);
    setOpen(false);
    onClear();
    inputRef.current?.focus();
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (!open) return;
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActiveIdx((i) => Math.min(i + 1, suggestions.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActiveIdx((i) => Math.max(i - 1, 0));
    } else if (e.key === "Enter" && activeIdx >= 0) {
      e.preventDefault();
      handleSelect(suggestions[activeIdx]);
    } else if (e.key === "Escape") {
      setOpen(false);
    }
  };

  // Scroll active item into view
  useEffect(() => {
    if (activeIdx >= 0 && listRef.current) {
      const item = listRef.current.children[activeIdx] as HTMLElement;
      item?.scrollIntoView({ block: "nearest" });
    }
  }, [activeIdx]);

  return (
    <div className="relative w-full max-w-sm">
      <div className="flex items-center bg-slate-800 border border-slate-600 rounded-lg overflow-hidden focus-within:border-indigo-500 transition-colors">
        <svg
          className="ml-3 shrink-0 text-slate-400 w-4 h-4"
          fill="none" viewBox="0 0 24 24" stroke="currentColor"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
            d="M21 21l-4.35-4.35M17 11A6 6 0 1 1 5 11a6 6 0 0 1 12 0z" />
        </svg>
        <input
          ref={inputRef}
          type="text"
          className="flex-1 bg-transparent px-3 py-2 text-sm text-slate-200 placeholder-slate-500 outline-none"
          placeholder="Search author…"
          value={query}
          onChange={(e) => handleChange(e.target.value)}
          onKeyDown={handleKeyDown}
          onFocus={() => suggestions.length > 0 && setOpen(true)}
          onBlur={() => setTimeout(() => setOpen(false), 150)}
        />
        {query && (
          <button
            onClick={handleClear}
            className="mr-2 text-slate-500 hover:text-slate-300 text-lg leading-none"
          >
            ×
          </button>
        )}
      </div>

      {open && (
        <ul
          ref={listRef}
          className="absolute left-0 right-0 mt-1 bg-slate-800 border border-slate-600 rounded-lg shadow-xl z-50 max-h-56 overflow-y-auto"
        >
          {suggestions.map((s, i) => (
            <li
              key={s}
              className={`px-3 py-2 text-sm cursor-pointer transition-colors ${
                i === activeIdx
                  ? "bg-indigo-600/40 text-white"
                  : "text-slate-300 hover:bg-slate-700"
              }`}
              onMouseDown={() => handleSelect(s)}
            >
              {s}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
