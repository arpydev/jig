import { placeOrder } from "./orders";
import { unusedHelper } from "./pricing";

export function main(): void {
  placeOrder(["apple", "pear"]);
}

export function neverCalled(): void {
  unusedHelper();
}
