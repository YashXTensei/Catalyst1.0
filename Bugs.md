## 1 : Refresh karne se baar baar dahsboard page pe chal jate ga [FIXED]
- Solution: Added hash routing (`#dashboard`, `#ask`, `#decisions`, `#pr`) and `localStorage` persistence for both `activeTab` and `currentRepo`. Now on browser refresh (F5), user stays on the exact same page and repository.

## 2 : Status Indexing not finishing [FIXED]
- Solution:
  1. Handled orphaned indexing statuses on server boot so crashes/restarts don't leave repos stuck in "indexing".
  2. Guaranteed status completion in `run_background_indexing` finally block.
  3. Added `reset-status` API endpoint and a "Reset Status" button on the UI if indexing ever takes too long.
  4. Optimized batch size for issue indexing to prevent rate limit timeouts.

## 3 : 502 Bad Gateway Error [FIXED]
- Root Cause:
  1. Backend was not running because `pydantic-settings` and `google-genai` were missing from Python environment, causing uvicorn startup to fail.
  2. `.env` file was missing (only `.env.example` existed).
- Solution:
  1. Installed missing packages (`pydantic-settings`, `google-genai`).
  2. Created `.env` from `.env.example`.
  3. Verified backend loads and connects to database and Gemini/GitHub APIs successfully.

  ## 4 : Improve Semantic Search 3072 dimensions ko 768 me karna ha 