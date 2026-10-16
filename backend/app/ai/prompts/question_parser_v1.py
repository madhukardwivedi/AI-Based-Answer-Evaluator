QUESTION_PARSER_PROMPT_VERSION = "question_parser_v1"
QUESTION_PARSER_PROMPT = """Extract this exam paper into the supplied schema. Preserve source wording, numbering, sections and order. Do not invent text, questions, marks, answers, solutions, concepts, notes, or rubric criteria. Keep explicit subquestion hierarchy and report uncertainty in warnings. Put the visible question identifier only in question_number, never at the start of question_text. For Q3(a), use question_number Q3(a), parent_question_number Q3, and omit Q3(a) from question_text.

Maximum marks are a high-priority extraction task. Inspect the complete page layout, especially right-aligned columns, below-question labels, tables, and subquestion rows. Capture only marks visibly printed in forms such as [2 marks], [2], (2 marks), (2), 2 marks, Marks: 2, M: 2, or 2M. Do not infer marks from ordering, totals, or typical values. If a mark is not visibly readable, use null and add a warning.

If the document explicitly includes evaluator/reference information, extract it into the matching optional fields for the correct question. Examples of source labels include Model Answer, Reference Answer, Key Concepts, Acceptable Alternatives, Reference Solution, Marking Notes, Marking Scheme, Rubric, and Evaluation Criteria. Preserve document wording faithfully.

If the document is a normal student-facing question paper and these reference fields are absent, return null for text fields and an empty rubric_criteria list. Never solve a question yourself. Never generate a model answer from general knowledge. Never infer a marking scheme that is not explicitly printed.

Support block-style reference documents such as:
Q1 - 3 marks
Question: ...
Model answer: ...
Key concepts: ...
Acceptable alternatives: ...
Reference solution: ...
Marking notes: ...

Support table-style documents conservatively when columns include Question, Maximum Marks, Reference Answer, Key Concepts, or Marking Scheme. Associate each row's reference data only with the question in that row.

For rubric_criteria, include only criteria explicitly present in the source. Each item must include criterion and maximum_marks; description may be null. Do not split ordinary model-answer prose into rubric criteria unless the source clearly labels it as a rubric, marking scheme, or evaluation criteria."""
