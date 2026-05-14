import { Controller } from "@hotwired/stimulus";
import * as Turbo from "@hotwired/turbo";

export default class extends Controller<HTMLElement> {
  static targets = ["input"];
  static values = { delay: { type: Number, default: 200 } };

  declare readonly inputTarget: HTMLInputElement;
  declare readonly delayValue: number;

  private timeout?: ReturnType<typeof setTimeout>;

  private onKeydown = (event: KeyboardEvent): void => {
    if (!(event.metaKey || event.ctrlKey)) return;
    if (event.key.toLowerCase() !== "k") return;
    event.preventDefault();

    this.inputTarget.focus();
    this.inputTarget.select();
  };

  connect(): void {
    document.addEventListener("keydown", this.onKeydown);
  }

  disconnect(): void {
    document.removeEventListener("keydown", this.onKeydown);
    if (this.timeout) clearTimeout(this.timeout);
  }

  query(event: Event): void {
    const value = (event.currentTarget as HTMLInputElement).value;
    if (this.timeout) clearTimeout(this.timeout);
    this.timeout = setTimeout(() => this.submit(value), this.delayValue);
  }

  clear(): void {
    // Programmatic value assignment doesn't fire 'input', so we skip the
    // debounce path and submit immediately.
    if (this.timeout) clearTimeout(this.timeout);
    this.inputTarget.value = "";
    this.inputTarget.focus();
    this.submit("");
  }

  private submit(value: string): void {
    const url = new URL(window.location.href);

    if (value) url.searchParams.set("q", value);
    else url.searchParams.delete("q");

    // action: "replace" so each keystroke doesn't pile up history entries.
    Turbo.visit(url.toString(), { action: "replace" });
  }
}
