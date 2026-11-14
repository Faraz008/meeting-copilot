<!--SYSTEM-->
You are a helpful assistant that extracts action items from meeting transcripts.
<!--USER-->
Meeting date: <<MEETING_DATE>>.
Read the transcript and list all action items, decisions and unanswered questions.
Return JSON only: {"action_items":[{"title":"","owner":"","deadline":"YYYY-MM-DD or null"}],"decisions":[""],"open_questions":[""]}

Transcript:
<<TRANSCRIPT>>
