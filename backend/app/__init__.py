"""Field punch list and RFI tracker with verified closeout.

Punch items and contractor RFIs are opened against a level, room and drawing
sheet, routed to a responsible discipline, aged on a clock that escalates
unanswered questions, and closed only against inspection evidence recorded
in an append-only event log. A room's turnover is refused, naming the exact
item still open, while any punch item or RFI in it is not closed.
"""
