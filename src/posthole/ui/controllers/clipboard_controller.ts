import { Controller } from "@hotwired/stimulus";

const FLASH_MS = 1500;

export default class extends Controller<HTMLElement> {
  static values = { text: String };
  static targets = ["defaultIcon", "successIcon"];

  declare readonly textValue: string;
  declare readonly defaultIconTarget: HTMLElement;
  declare readonly successIconTarget: HTMLElement;
  declare readonly hasDefaultIconTarget: boolean;
  declare readonly hasSuccessIconTarget: boolean;

  private timer?: number;

  /** Copy ``textValue`` to the clipboard and briefly swap the icon. */
  async copy(): Promise<void> {
    if (!navigator.clipboard?.writeText) return;
    try {
      await navigator.clipboard.writeText(this.textValue);
    } catch {
      return;
    }
    this.flash();
  }

  disconnect(): void {
    if (this.timer !== undefined) window.clearTimeout(this.timer);
  }

  private flash(): void {
    if (!this.hasDefaultIconTarget || !this.hasSuccessIconTarget) return;

    this.defaultIconTarget.classList.add("hidden");
    this.successIconTarget.classList.remove("hidden");

    if (this.timer !== undefined) window.clearTimeout(this.timer);
    this.timer = window.setTimeout(() => {
      this.defaultIconTarget.classList.remove("hidden");
      this.successIconTarget.classList.add("hidden");
      this.timer = undefined;
    }, FLASH_MS);
  }
}
