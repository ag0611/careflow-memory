# Feedback on Nebius Token Factory and NVIDIA Nemotron

Project: CareFlow Memory (Personal AI track)
Builder: Aadi, first-year B.Tech IT student, building solo
Written while building, Oct 27, 2026. Items marked **TO FILL** need a live-mode test and will be completed before submission.

## 1. Onboarding and access (observed Oct 27, 2026)

| Area | What happened | Suggestion |
| --- | --- | --- |
| Hackathon page | The Devpost page names the Nemotron 3 Nano, Super and Ultra tiers, but gives no exact API model IDs or base URL. I started with guessed IDs (`nvidia/nemotron-3-nano`, `-super`, `-ultra`) and a documented-looking base URL, and had to leave a note in the README to verify them in the console. | Add a short "Quick start" block to the Resources tab: base URL, exact model IDs for each Nemotron tier, and a 5-line Python example using the OpenAI-compatible client. |
| Promo code flow | I used the hackathon promo link. The page said "Form submitted. The promo code will be emailed to you." No email had arrived in my inbox at the time of writing, with a deadline three days away. | Show the code on the confirmation page, or state the expected delivery time. Add a resend option or a support contact on the same page. |
| Account setup | Signing up for the console asked for card and address details before I could reach an API key. As a student participant this was a real barrier, and I was not sure whether the hackathon credits would be used first or whether the card could be charged. | State clearly on the signup screen whether a card is required for hackathon credits, and that nothing is charged while promo credits remain. Offer a no-card path for hackathon participants if possible. |
| Time cost | Because of the above, I built and tested the whole app in an offline fallback mode first, so that the project would not be blocked by access. | A key that works within minutes of registering for the hackathon would let participants test live models from day one. |

## 2. Model IDs and endpoint

| Date | Area | What happened | Suggestion |
| --- | --- | --- | --- |
| Oct 27 | Model IDs | **TO FILL**: which exact IDs the models list returned for Nano, Super and Ultra, and whether my guessed IDs worked. | **TO FILL** |
| Oct 27 | Base URL / OpenAI compatibility | **TO FILL**: did the standard `openai` Python client work by only changing `base_url` and `api_key`? Any differences in parameters? | **TO FILL** |

## 3. Model behaviour (measured in CareFlow Memory)

| Area | Result | Suggestion |
| --- | --- | --- |
| Latency, Ultra vs Super on the same shift handover | **TO FILL**: numbers from the Models page "Run comparison" (seconds, tokens in and out) | **TO FILL** |
| Latency, Nano for the scope check and note extraction | **TO FILL** | **TO FILL** |
| Average chat latency with Super | **TO FILL** (target: under 5 s) | **TO FILL** |
| JSON mode / structured output | **TO FILL**: does `response_format: json_object` work for each tier, and how often was the output invalid? | **TO FILL** |
| Instruction following on safety rules | **TO FILL**: did the models stay within "administrative only, no clinical advice"? Any red-team prompts that got through the model layer? | **TO FILL** |
| Fallback behaviour | **TO FILL**: errors or timeouts observed, and whether Ultra to Super to Nano fallback was triggered | **TO FILL** |

## 4. Docs, console and limits

| Area | What happened | Suggestion |
| --- | --- | --- |
| Rate limits and quotas | **TO FILL** | **TO FILL** |
| Pricing visibility | **TO FILL**: was it clear what each call costs against the credits? | **TO FILL** |
| Console usage view | **TO FILL**: could I see token usage per model while testing? | **TO FILL** |

## 5. What worked well

**TO FILL** after live testing. Candidate points to verify before claiming them:

- A routing design with three tiers (Nano, Super, Ultra) fits the app naturally: cheap, fast calls for scope checks, balanced calls for chat, and the strongest model only for handovers.
- Keeping every model call behind one small client with a measured latency log made the Ultra vs Super comparison easy to produce.

## 6. Feedback on my own product (CareFlow Memory)

**TO FILL** after showing the demo to 3 to 5 people. Planned questions: Was the Today page clear? Did the confirm card feel safe? Was the handover note something you would sign? What was missing?

## 7. Feature requests (summary)

1. Publish exact model IDs and a base URL in the hackathon Resources tab.
2. Make the promo code visible immediately, or give a delivery time and a resend option.
3. Clarify whether a card is required for hackathon credits, and offer a no-card route for participants.
4. **TO FILL** after live testing.
