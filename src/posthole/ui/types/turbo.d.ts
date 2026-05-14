// @hotwired/turbo 8.x ships UMD/ESM but no .d.ts. Declare the surface we use.
declare module "@hotwired/turbo" {
  export type TurboVisitAction = "advance" | "replace" | "restore";

  export interface TurboVisitOptions {
    action?: TurboVisitAction;
    frame?: string;
  }

  export function visit(location: string | URL, options?: TurboVisitOptions): void;
}
