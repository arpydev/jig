import { expandTree, placeOrder } from "./orders";
import { unusedHelper } from "./pricing";

export function main(): void {
  placeOrder(["apple", "pear"]);
  expandTree(2);
}

export function neverCalled(): void {
  unusedHelper();
}
