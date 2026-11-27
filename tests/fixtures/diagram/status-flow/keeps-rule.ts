export enum TicketStatus {
  Open = "open",
  InProgress = "in_progress",
  Resolved = "resolved",
  Closed = "closed",
}

export class Ticket {
  status = TicketStatus.Open;

  start() {
    if (this.status !== TicketStatus.Open) throw new Error("only an open ticket can be started");
    this.status = TicketStatus.InProgress;
  }

  resolve() {
    if (this.status !== TicketStatus.InProgress) throw new Error("only a ticket in progress can be resolved");
    this.status = TicketStatus.Resolved;
  }

  reopen() {
    switch (this.status) {
      case TicketStatus.Resolved:
      case TicketStatus.Closed:
        this.status = TicketStatus.Open;
        break;
      default:
        throw new Error("only a resolved or closed ticket can be reopened");
    }
  }

  close() {
    if (this.status !== TicketStatus.Resolved) throw new Error("only a resolved ticket can be closed");
    this.status = TicketStatus.Closed;
  }
}
