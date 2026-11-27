import { formatLine } from "tiny-format";
import { priceOf, walkTree } from "./pricing";

export function placeOrder(items: string[]): number {
  const total = items.map((item) => priceOf(item)).reduce((a, b) => a + b, 0);
  console.log(formatLine(`total ${total}`));
  expandTree(items.length);
  return total;
}

export function expandTree(depth: number): number {
  return depth <= 0 ? 0 : walkTree(depth - 1);
}

export function cancelOrder(): void {}
