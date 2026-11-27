import { expandTree } from "./orders";

export class Discounts {
  apply(value: number): number {
    return roundPrice(value * 0.9);
  }
}

export function priceOf(item: string): number {
  return new Discounts().apply(item.length * 1.5);
}

function roundPrice(value: number): number {
  return Math.round(value);
}

export function walkTree(depth: number): number {
  return expandTree(depth) + 1;
}

export function unusedHelper(): number {
  return 0;
}
