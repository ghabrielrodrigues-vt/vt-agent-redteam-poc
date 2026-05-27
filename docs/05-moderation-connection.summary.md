# Nerdy Tutor Moderation Connection — Non-Technical Summary

## What looks the same and what is actually different

When the action item stated "we have some logic that is largely copied", that was
right — **but only at a high level**. At the level where you actually write code, the
two things are different jobs.

The Nerdy Tutor moderation work from recent weeks is like a **bouncer at the AI's
door**. When a student types something risky, the bouncer decides whether to let the
message in. If yes, the AI sees it; if no, the AI never learns the student tried.

The red-team POC is like a **mystery shopper**. It approaches the AI, says something
designed to make it stumble, listens to what the AI answers, and grades whether the AI
did well. The point **is not to protect the AI from bad input** — it is **to verify
the AI behaves well when something bad gets through**.

Both jobs are necessary. You want a bouncer **and** mystery shoppers. They check
different failure modes.

## What from the moderation work I will reuse

The work was not duplicated. Three concrete pieces transfer directly to the red-team
POC:

1. **The list of risky prompts and categories.** I spent weeks curating the
   education-specific list of bad words, phrases, and intents that appear in our
   tutoring context. That list becomes the **initial menu** of test prompts the
   red-team tool sends to the AI. A team starting from scratch would need months of
   incident review to build something equivalent.

2. **The OpenAI Moderation API integration.** I plugged OpenAI's safety classifier
   into the moderation pipeline to decide whether incoming text is risky. The red-team
   POC uses **the same classifier** to decide whether the response the AI is sending is
   risky. Same code patterns, opposite direction.

3. **How we store data.** The schema, categorization, language-code handling, JSON
   detail pattern — I built all of that for the moderation database. The red-team POC
   reuses the same conventions for the results table so anyone reading either table
   feels at home.

## What I cannot reuse, and why that is fine

Two things must stay behind:

1. **The pipeline architecture itself.** The L1/L2/L3 stack lives inside the
   student-onboarding repo as a Next.js server route. It is not a library yet, and
   extracting it is a different project. For the red-team POC, I do not need the stack
   — only pieces of its inputs and one of its API calls.

2. **The idea of "block before the AI sees it".** LiveKit voice has no step where I
   can intercept user speech before the AI listens; by the time audio arrives, it is
   already inside the AI's internal speech-to-text. That is fine. Blocking inputs is
   the production moderation pipeline's job. Testing outputs is the red-team POC's
   job.

## What I will tell the team

The story I will defend in the spike doc is:

> "The moderation work I did (PR #1667 and PR #1669) ships as **production input
> filtering** — the bouncer. The red-team POC ships as a **separate Python package**
> that each LiveKit agent repo can import — the mystery shopper. They share
> categories, the OpenAI Moderation call, and storage patterns, but run in different
> places, at different times, for different goals."

That is honest, defensible, and clear. It avoids overselling — saying "this unifies
all moderation" would be technically wrong and invite criticism.
