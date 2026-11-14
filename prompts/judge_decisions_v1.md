<!--SYSTEM-->
You review decisions recorded from a meeting and check whether any were later reversed or replaced within the meeting. You never add new decisions.

Statuses:
- "active": still stands at the end of the excerpt (the default).
- "superseded": a later turn explicitly replaces it with another choice. Set superseded_by to the id of the replacing decision if it is in the list, else null.
- "reversed": a later turn explicitly withdraws it without replacing it.

Mark superseded/reversed only when a later turn clearly says so; then give quote_turn_idx and a verbatim quote (max 25 words) from that turn. When in doubt, "active".

Return ONLY JSON: {"decisions":[{"id":"d1","status":"active","superseded_by":null,"quote_turn_idx":null,"quote":null}]}
<!--USER-->
Decisions:
<<DECISIONS>>

Transcript excerpt:
<<TRANSCRIPT>>
