import { Controller } from "@hotwired/stimulus";

export default class extends Controller<HTMLElement> {
  static targets = ["output"];

  declare readonly outputTarget: HTMLElement;

  connect(): void {
    this.outputTarget.textContent = "stimulus loaded";
  }
}
