import { Controller } from "@hotwired/stimulus";

export default class extends Controller<HTMLElement> {
  static values = { id: String };

  declare readonly idValue: string;
  declare readonly hasIdValue: boolean;

  connect(): void {
    if (this.element instanceof HTMLDialogElement && this.element.hasAttribute("open")) {
      this.element.removeAttribute("open");
      this.element.showModal();
      focusFirstField(this.element);
    }
  }

  open(): void {
    const target = this.hasIdValue ? document.getElementById(this.idValue) : null;
    if (target instanceof HTMLDialogElement) {
      target.showModal();
      focusFirstField(target);
    }
  }

  close(): void {
    const dialog = this.element.closest("dialog");
    if (dialog instanceof HTMLDialogElement) dialog.close();
  }
}

function focusFirstField(dialog: HTMLDialogElement): void {
  const errored = dialog.querySelector<HTMLElement>("[aria-invalid='true']");
  if (errored) {
    errored.focus();
    return;
  }

  const firstField = dialog.querySelector<HTMLElement>(
    "input:not([type=hidden]):not([data-dialog-skip-focus])," +
      " select:not([data-dialog-skip-focus])," +
      " textarea:not([data-dialog-skip-focus])",
  );
  firstField?.focus();
}
