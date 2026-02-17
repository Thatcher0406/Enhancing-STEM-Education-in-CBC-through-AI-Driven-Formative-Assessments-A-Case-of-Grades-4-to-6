# CBC AI Formative Assessment Report

## 1. Executive Summary
Built an end-to-end CBC-aligned formative assessment prototype for Grades 4-6: Streamlit learner UI (frontend/), FastAPI backend (backend/), SQLite persistence (app.db), and an LLM quiz engine (Mistral 7B Instruct) that generates MCQs scoped to KICD topics. Achieved adaptive Bloom-level selection based on recent learner performance and per-question rationale feedback.

## 2. Architecture Overview
- Frontend: Streamlit app (frontend/app.py, pages/*) handling parent auth, child profiles, topic selection, quiz rendering, scoring, and review.
- Backend: FastAPI service (backend/) with OTP + Google OAuth, quiz history persistence (SQLite), Bloom-level adaptivity, and a proxy to the LLM quiz engine.
- Quiz Engine: Colab/Ngrok Flask microservice (notebooks/mistral.ipynb.ipynb) running Mistral-7B-Instruct in 4-bit via BitsAndBytes, enforcing JSON-only MCQ output.
- Data/Persistence: SQLite tables quiz_attempts and quiz_attempt_details store scores, Bloom level, and per-question choices/rationales.

## 3. Data & Curriculum Alignment
- Topics sourced from KICD designs, hard-coded per grade/subject (frontend/pages/subject_page.py) and mirrored in the quiz engine.
- Each quiz request carries subject, normalized grade (int for the engine), and topic; backend validates and forwards to the LLM with Bloom metadata.
- Kenyan context and SI units enforced in the system prompt; single-correct MCQs with rationales.

## 4. Adaptivity Logic
- History summary (backend/routes/quiz.py): last three attempts per subject/topic, average score, weak stems, avoid repeats.
- Bloom ladder: Remember -> Understand -> Apply -> Analyze -> Evaluate -> Create.
- Auto Bloom selection: step up when last score >= 85%, step down when <= 50%; otherwise use average/last Bloom.
- Adaptive context sent to the model includes weak spots and prior stems to discourage repetition.

## 5. Quiz Flow
1) Learner selects subject/topic (with grade inferred from profile).
2) UI calls POST /quiz/generate with profile_id, subject, topic, Bloom (or Auto).
3) Backend enriches with history, chooses Bloom, forwards to quiz engine, then normalizes output for UI (answer_idx, options array, rationale).
4) Learner answers; UI computes score, shows rationales, and posts POST /quiz/submit with per-question detail.
5) History available via /quiz/recent and /quiz/attempt/{id} for review.

## 6. Current Validation
- Manual smoke tests across Math/Science topics: valid JSON returned, Bloom coercion works when Auto, scores persist, and review renders correctly.
- No automated item analytics yet; psychometric metrics pending real learner data.

## 7. Key Challenges
- LLM output variance: occasional JSON malformation; needs stronger schema validation/retry.
- Topic fidelity: depends on prompt + pre-filtered list; lacks secondary semantic check against KICD text.
- Latency: Mistral 7B (4-bit, CPU/Colab) incurs seconds per request; may need caching or a distilled model.
- Data sparsity: Adaptivity heuristics run on limited mock history until real learner logs arrive.

## 8. Production Improvements
Short-term (1-2 weeks):
- Add JSON schema validation + retry/repair loop for quiz engine responses.
- Contract tests for /quiz/generate and /quiz/submit.
- Thresholded fallback to a cached template bank on engine failure.

Medium-term (1-2 months):
- Topic-classifier gate to reject off-curriculum generations; load KICD topics from a canonical file instead of inline constants.
- Item analytics: difficulty/discrimination per stem; adjust Bloom using mastery estimates.
- UX: preload topics per profile, offline fallback quizzes, text-to-speech/read-aloud.

Long-term (3-6 months):
- Serve a quantized/distilled model (GPTQ/INT8) or cached bank for common topics; add rate limits and tracing.
- Active learning loop: flag low-confidence generations for human review and continuous fine-tuning.
- Fairness/bias checks on LLM outputs (gendered language, cultural bias).

## 9. Deployment Notes
- Backend: FastAPI on Uvicorn; requires QUIZ_ENGINE_URL, QUIZ_API_KEY, GOOGLE_CLIENT_ID/SECRET/REDIRECT_URI, FRONTEND_URL in .env.
- Frontend: Streamlit; set BACKEND_URL in frontend/.streamlit/secrets.toml or env.
- Quiz engine: Run notebooks/mistral.ipynb.ipynb in Colab with HF token, Ngrok token, and the KICD topic file (cbc_topics.jsonl).

## 10. Next Steps
- Option 1: Ingest real Grade 4-6 learner logs to tune adaptivity and compute item stats.
- Option 2: Harden the quiz engine (schema validation, retries, monitoring) and add cached fallbacks.
- Option 3: Pilot with teachers to verify KICD alignment and Bloom suitability, then iterate on prompts and topic coverage.
