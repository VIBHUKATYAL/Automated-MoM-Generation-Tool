# Sample Meeting Transcripts with Reference MoM

## Meeting 1 — Website Sprint Review

**Date:** 28 September 2026  
**Duration:** 25 minutes  
**Participants:** Rahul (PM), Priya (Frontend), Arjun (Backend), Karan (QA)

### Transcript

**Rahul:** Let's start with the website sprint review. Priya, how is the homepage redesign?

**Priya:** The desktop version is complete. I fixed the spacing issues in the hero section and updated the navigation bar. The mobile version still needs some work.

**Rahul:** What is left on mobile?

**Priya:** The product cards are overflowing on smaller screens. I'll fix the responsive layout by tomorrow evening.

**Arjun:** On the backend side, the product API is ready. I also added pagination so we don't load all products at once.

**Karan:** I tested the API today. Pagination works, but I found one issue where an empty page returns a server error.

**Arjun:** Okay, I'll fix that and add a test for empty results.

**Rahul:** Good. Karan, can you retest the API after Arjun's fix?

**Karan:** Yes, I'll retest it tomorrow.

**Rahul:** Anything else?

**Priya:** No. Once the mobile layout is fixed, I'll send the updated build to QA.

**Rahul:** Great. Let's target the staging deployment for Friday.

### Reference MoM

**Summary:**  
The team reviewed the website sprint progress. The homepage desktop redesign and product API are mostly complete, while mobile responsiveness and an API empty-page error remain to be fixed.

**Key Points:**
- Homepage desktop redesign completed.
- Mobile product cards have a responsive layout issue.
- Product API pagination has been implemented.
- Empty API result pages currently return a server error.
- Updated frontend build will be sent to QA after the mobile fix.

**Decisions:**
- The team will target staging deployment for Friday.

**Action Items:**
1. **Priya** — Fix the mobile product-card responsive layout by tomorrow evening.
2. **Arjun** — Fix the empty-page API error and add a corresponding test.
3. **Karan** — Retest the API after Arjun's fix.

**Next Meeting Scheduled:** Not explicitly scheduled.

---

## Meeting 2 — Marketing Campaign Planning

**Date:** 29 September 2026  
**Duration:** 20 minutes  
**Participants:** Neha (Marketing Lead), Aman (Content Writer), Riya (Designer)

### Transcript

**Neha:** We need to finalize the launch campaign for the new product.

**Aman:** I have prepared three announcement posts and two short-form video scripts.

**Neha:** Good. Please revise the second announcement post. The message is too technical.

**Aman:** Sure, I'll simplify it and send the revised version by Wednesday.

**Riya:** I've completed the first two social media creatives. The third creative is waiting for the final copy.

**Neha:** Once Aman sends the revised copy, I'll review it and send it to Riya.

**Riya:** Perfect. I can finish the third creative on Thursday.

**Neha:** Let's publish the first announcement on Friday morning.

**Aman:** Should we also prepare an email announcement?

**Neha:** Yes. Please draft a short email announcement as well.

**Aman:** I'll include that with the revised post on Wednesday.

**Riya:** I'll make sure all three creatives use the same visual style.

**Neha:** Great. We'll review everything together on Thursday afternoon.

### Reference MoM

**Summary:**  
The marketing team planned the product launch campaign, including social media posts, video scripts, creatives, and an email announcement.

**Key Points:**
- Three announcement posts are being prepared.
- Two short-form video scripts are ready.
- The second announcement post needs simpler language.
- Two social media creatives are complete.
- A third creative is waiting for the revised copy.
- An email announcement will also be prepared.

**Decisions:**
- The first announcement will be published on Friday morning.
- The team will review the complete campaign on Thursday afternoon.

**Action Items:**
1. **Aman** — Simplify the second announcement post and prepare the email announcement by Wednesday.
2. **Riya** — Complete the third social media creative on Thursday.
3. **Neha** — Review the revised copy and send the final version to Riya.

**Next Meeting Scheduled:** Thursday afternoon for the campaign review.

---

## Meeting 3 — Database Performance Discussion

**Date:** 30 September 2026  
**Duration:** 30 minutes  
**Participants:** Vikram (Backend Lead), Meera (Database Engineer), Sameer (Developer), Anjali (QA)

### Transcript

**Vikram:** We have noticed that the dashboard is becoming slow when loading large datasets.

**Meera:** I checked the database queries. The main dashboard query is scanning too many rows because the date column is not indexed.

**Sameer:** Can we add an index without changing the application code?

**Meera:** Yes. The current query can use an index on the `created_at` column. I'll test the impact first.

**Anjali:** Do we have to test old reports after the index is added?

**Meera:** Yes. The reports should return exactly the same results.

**Vikram:** Let's test this in staging before applying it to production.

**Sameer:** I can prepare the staging migration today.

**Meera:** Good. I'll review the migration and run performance tests.

**Anjali:** I'll compare the old and new report results after the migration.

**Vikram:** If everything passes, we'll deploy the database change tomorrow evening.

**Meera:** That works for me.

### Reference MoM

**Summary:**  
The team investigated slow dashboard performance and identified a missing database index on the `created_at` column as a likely cause.

**Key Points:**
- Dashboard queries scan too many database rows.
- The `created_at` column is currently not indexed.
- An index may improve dashboard query performance.
- The change will first be tested in staging.
- Existing reports must continue returning the same results.

**Decisions:**
- The database change will be tested in staging before production deployment.
- Production deployment is planned for tomorrow evening if testing passes.

**Action Items:**
1. **Sameer** — Prepare the staging database migration today.
2. **Meera** — Review the migration and perform performance tests.
3. **Anjali** — Compare report results before and after the migration.

**Next Meeting Scheduled:** Not explicitly scheduled.
