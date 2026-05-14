import { Controller } from "@hotwired/stimulus";

const PRESETS = ["iphone-14-pro", "iphone-14", "iphone-8", "google-pixel-6-pro"] as const;
type Preset = (typeof PRESETS)[number];
const STORAGE_KEY = "posthole:phone-preset";
const DEFAULT_PRESET: Preset = "iphone-14-pro";

export default class extends Controller<HTMLElement> {
  static targets = ["device", "chip"];

  declare readonly deviceTarget: HTMLElement;
  declare readonly hasDeviceTarget: boolean;
  declare readonly chipTargets: HTMLButtonElement[];
  declare readonly hasChipTarget: boolean;

  private current: Preset = DEFAULT_PRESET;

  connect(): void {
    this.current = readSavedPreset();
    this.render();
  }

  select(event: Event): void {
    const next = (event.currentTarget as HTMLElement).dataset.preset;
    if (!next || !isPreset(next)) return;
    this.current = next;
    try {
      localStorage.setItem(STORAGE_KEY, next);
    } catch {
      // private mode / disabled storage — selection still applies for the
      // current session, just won't persist
    }
    document.documentElement.setAttribute("data-phone-preset", next);
    this.render();
  }

  private render(): void {
    if (this.hasDeviceTarget) {
      for (const p of PRESETS) {
        this.deviceTarget.classList.toggle(`device-${p}`, p === this.current);
      }
    }

    if (this.hasChipTarget) {
      for (const chip of this.chipTargets) {
        const match = chip.dataset.preset === this.current;
        chip.toggleAttribute("data-active", match);
        chip.setAttribute("aria-pressed", match ? "true" : "false");
      }
    }
  }
}

function isPreset(value: string): value is Preset {
  return (PRESETS as readonly string[]).includes(value);
}

function readSavedPreset(): Preset {
  try {
    const v = localStorage.getItem(STORAGE_KEY);
    if (v && isPreset(v)) return v;
  } catch {
    // ignore
  }
  return DEFAULT_PRESET;
}
