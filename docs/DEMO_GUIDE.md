# Demo walkthrough: from empty database to reviewed results

Complete the [README setup](../README.md) first. Keep the backend, frontend, database and chosen AI provider running. Use http://localhost:3000. This guide describes the current UI; it does not promise perfect AI output or fixed grades.

## Before you begin

- Use the synthetic [demo files](../demo/README.md), not real student information.
- Start with one student, Rahul (101); add the other sheets after the first run succeeds.
- A **model answer** means a teacher's reference answer, not the name of an AI model. A **rubric** is a list of scoring criteria with marks.
- **Transcription** copies the student's work, including wrong work. **Mapping** assigns it to an exam question. **Evaluation** suggests marks. **Finalization** happens only after faculty review.
- AI may omit lines or misread labels even with high reported confidence. Confidence is not a calibrated probability. Compare every answer with the source scan.

## 1. Login and create the Maths exam

1. Login with the evaluator email/password you created during setup.
2. Open Exams and create an exam: name `Class 10 Maths Demo`, subject `Mathematics`, class `10`, total marks `50`.
3. Open that exam. Its tabs are Questions, Students, Answer Sheets, Question Paper, Extraction, Evaluation and Results.
4. Dashboard is a useful entry point, but its evaluated/pending counters are currently incomplete. Use the submission summary on Evaluation for real progress.

Expected checkpoint: a fresh exam with no imported questions or student uploads.

## 2. Upload, parse and review the question paper

1. Open Question Paper and choose [class10_math_exam_50_marks.pdf](../class10_math_exam_50_marks.pdf) from the cloned project folder.
2. Click **Upload question paper**, then **Parse / reparse**. Wait for the request to finish.
3. Review each candidate. The source paper has exactly these 12 items:

   `Q1, Q2, Q3, Q4, Q5, Q6, Q7, Q8, Q9, Q10(a), Q10(b), Q11`.

4. Verify marks: Q1–Q5 = 2 each; Q6–Q9 = 5 each; Q10(a) = 5; Q10(b) = 5; Q11 = 10. Total = 50. Check sequence order 1–12. Q10 subquestions have parent number Q10; do not invent a separately marked parent question.
5. Fix any missing marks, duplicated identifiers or shortened text before import. Do not import duplicate candidate blocks. Compare with the PDF rather than assuming a successful HTTP response means perfect parsing.
6. **Known demo label mismatch:** the answer sheets print `Q3(a)` for the paper's `Q3`. For this controlled demo, change that candidate's identifier to `Q3(a)` before import and clear its parent field (there is no separate Q3 parent). Alternatively keep Q3 and explicitly map the student's Q3(a) to Q3 during review. This is a source-file mismatch, not an extra question.
7. Select the desired candidates and click **Import selected questions**. This is explicit: parsing alone never imports.
8. Open Questions and check there are exactly 12 entries totaling 50 marks. If an import skips a duplicate or missing mark, read the message, correct the candidate, and retry only the missing item.

Reparse replaces the saved candidate set; it does not replace previously imported questions. Deleting/replacing the question-paper upload does not silently update those questions either.

## 3. Configure model answers and rubrics

The Maths PDF is a student-facing paper and contains no answer key. AI parsing must not invent one.

1. Open [MATHS_REFERENCE.md](MATHS_REFERENCE.md) alongside the application.
2. On Questions, click **Edit** for each question. Copy its teacher reference into **Model answer**, confirm maximum marks and sequence, then save. Optional fields include key concepts, acceptable alternatives, reference solution and marking notes.
3. For Q1, demonstrate **Add criterion** twice: `Correct prime factorization of both numbers` (1 mark), then `Correct common factors and HCF 12` (1 mark). Use distinct sequence orders 1 and 2. The sum must not exceed Q1's maximum 2.
4. Try editing one criterion, saving, and cancelling another edit. Add a temporary criterion only on a disposable question if you want to demonstrate deletion.

Expected checkpoint: each question has usable reference data. Q1 also has a visible two-criterion rubric. Questions with neither reference data nor rubric cannot be evaluated.

## 4. Add/import students

1. Open Students.
2. Import [samples/student-roster-sample.csv](../samples/student-roster-sample.csv). It has five synthetic students, including the four answer-sheet owners.
3. Confirm Rahul 101, Priya 102, Aman 103, Sneha 104 and Arjun 105 appear.
4. Demonstrate manual addition of a temporary student with a new roll number, edit the name, then delete with confirmation.
5. Try individual checkboxes, Select All and Clear Selection. Selection itself does not delete students.
6. Optional: import the same CSV again to show duplicate-skipping feedback. Do not create the same students manually first unless demonstrating that behavior. XLSX uses the same headers as CSV.

Arjun has no supplied submission. A student with no upload is not automatically awarded zero or treated as evaluated.

## 5. Upload Rahul's answer sheet

1. Open Answer Sheets, select **Rahul Sharma — 101**.
2. Choose [class10_math_sample_answer_sheet_rahul_101.pdf](../class10_math_sample_answer_sheet_rahul_101.pdf), or drag it onto the upload area.
3. Upload and confirm its filename, student and uploaded status appear.
4. Click **Process / Extract** once. The app renders and processes all three pages. Wait for completion; local vision may take several minutes.
5. Open Extraction and select Rahul's submission if it is not already selected.

The upload selects a student manually. It does not detect student identity automatically. Keep the first demo to one complete PDF per student; the hardened database supports more complex links, but the current UI is not a combined-PDF splitting tool.

## 6. Review extraction and mapping

1. Check the answer count against the sheet: ideally 12 logical answers, including Q10(a) and Q10(b) separately.
2. Use **Previous**, **Next**, and the answer dropdown. The left panel displays the first relevant rendered source page; check additional pages in the original PDF when an answer spans pages.
3. Check the mapped question heading, marks and detected label. A unique matching label should show **Auto mapped**.
4. For a missing/ambiguous mapping, choose the correct question in the mapping dropdown, or click **Correct mapping**. Ensure Q3(a) corresponds to the distance question, not a new question.
5. Compare every line of the extracted answer with the image. Correct OCR omissions or misread symbols in **AI extracted answer**, then click **Save correction**. Saving marks the item reviewed and preserves the original raw transcription separately.
6. Never improve a student's solution. Even Rahul's sample contains arithmetic/factorization inconsistencies: copy the visible work, then judge it during evaluation.

For Aman Q2, a faithful transcript must retain:

```text
3x - 7 = 11
3x = 4
x = 4/3
```

It must not be rewritten to `3x = 18` and `x = 6`. If a model omits work, enter the actual visible missing lines. Do not assume all 12 answers were extracted just because processing completed. Do not mark an omitted answer as unanswered unless the scan truly contains no response.

Expected checkpoint: all detected answers are reviewed, mapped appropriately, and faithful to the scans. The model can still fail this check; human correction remains part of the demo.

## 7. Evaluate and review marks

1. Open Evaluation and select Rahul's submission.
2. Verify each card shows its mapped question, marks, effective student text and reference data. Saved faculty transcription corrections are used for evaluation.
3. An unmapped answer must be mapped in Extraction first. Do not try to evaluate it.
4. Click **Evaluate** for Q1 first. Check the rubric breakdown and suggested total.
5. Click **Evaluate all mapped answers** for the remaining answers. Wait for the sequential calls; inspect any per-answer errors. There is no guaranteed fixed score across AI providers/runs.
6. For one answer, change **Faculty marks**, add a short remark, and click **Modify & Save**. Keep the value between zero and that question's maximum. With rubric criteria, review any criterion overrides as well.
7. For other answers, review the evidence/feedback and click **Accept AI marks** when justified.
8. If transcription needs changing, return to Extraction, save it, and evaluate again. Corrections can invalidate the old evaluation. **Re-evaluate** runs another AI request; it is not required on every visit.

If a question genuinely has no answer in the scanned file, use **Confirm Q…: 0/…** only after verifying it. This records faculty-confirmed unanswered status. Missing AI extraction is not evidence that the student skipped a question.

## 8. Finalize, inspect results, export

1. Ensure every configured question has an evaluated, faculty-reviewed answer or confirmed unanswered record.
2. Click **Finalize evaluation**. If disabled, inspect the mapped/evaluated/reviewed counts and missing-question section.
3. Open Results. Confirm student, question-wise marks, total, maximum, percentage and status.
4. Manually add the final marks and compare with the total. With all 12 demo questions configured, the denominator is 50. For example, 40/50 is 80%; this is an arithmetic example, not a promised AI result.
5. Download CSV and XLSX. Open them in Excel, Numbers or LibreOffice. They contain student/roll, question-wise final marks, total, maximum, percentage and status. AI/faculty details are visible in Evaluation; the current exports are summary exports, not a full audit report.

Results can show in-progress submissions too. Check finalized status before presenting a total as final. PDF export is not available.

## 9. Try the remaining synthetic students

Repeat steps 5–8 with the matching files:

| Student | Roll | File |
|---|---|---|
| Priya Verma | 102 | [Priya PDF](../class10_math_answer_sheet_priya_verma_102.pdf) |
| Aman Gupta | 103 | [Aman PDF](../class10_math_answer_sheet_aman_gupta_103.pdf) |
| Sneha Reddy | 104 | [Sneha PDF](../class10_math_answer_sheet_sneha_reddy_104.pdf) |

These sheets intentionally include errors/partial work for faculty review. They are synthetic image-only examples, not a benchmark of real handwriting accuracy. Do not copy the teacher answer key into a student's transcript.

## 10. Optional parsing demonstrations (separate exams)

- **Digital vs scanned Science:** create a fresh Science exam with 20 marks. Parse the digital Phase 3 paper, then compare the scanned version in another fresh exam. Expected six candidates: Q1, Q2, Q3(a), Q3(b), Q4, Q5 with marks 2, 3, 2, 1, 5, 7. These files have no reference answers.
- **Reference extraction:** create a fresh Science exam with 25 marks. Upload `demo/demo_class10_science_evaluation_reference.pdf` through Question Paper, parse, review all seven questions and explicit reference fields, then import. The plain `demo_class10_science_question_paper.pdf` is the student-facing version and should not invent references. Use separate exams for comparison; duplicate import will not enrich existing questions automatically. No matching student answer sheet is supplied for this seven-question Science set.
- **Standalone scanned Science sheet:** `sample_scanned_answer_sheet.pdf` is a different 20-mark exam with four 5-mark questions. Configure those four questions and teacher references manually if using it; do not mix it with the six-question or seven-question papers.

## 11. Demonstrate edit/delete/reset safely

Use a disposable exam for destructive demonstrations.

| Action | What to demonstrate / effect |
|---|---|
| Question add/edit/cancel | Add a temporary question, edit it, then cancel or save. |
| Question selection/bulk delete | Select temporary questions; Delete Selected asks confirmation and removes associated rubrics. |
| Criterion edit/delete | Edit a criterion; deleting it affects future grading configuration. |
| Student delete | Confirm deletion; dependent submissions/results may be removed. Never demonstrate on the final reviewed student. |
| Question-paper delete/replace | Removes upload/parse result, not imported question rows. |
| Delete extracted answer | Removes that answer and dependent evaluation; retains the uploaded source. |
| Reset extraction | Removes extracted answers, mappings, faculty corrections and dependent evaluations/results; retains source. Process again from Answer Sheets afterward. |
| Reset all evaluations | Removes evaluations/faculty marks while keeping extraction/mapping. |
| Answer-sheet delete | Removes source file and dependent data subject to shared-source protections. Read the confirmation. |

Reset is not undo. Export final results first if you need them. To repeat a demo without losing work, create a new exam rather than resetting the reviewed one.

## Suggested presentation order

Login → open Maths exam → show source question paper → show imported questions/reference/rubric → Students → Rahul upload → Process / Extract → compare scan/text → correct one transcription → Evaluate → override one mark → accept others → Finalize → Results → export.

For a presentation, install/download models and rehearse beforehand. Preprocessed data may be shown to avoid long waits, but say clearly which AI steps were run earlier. Do not promise identical marks or extraction counts on every live run.
