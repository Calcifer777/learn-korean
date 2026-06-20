# Spaced Repetition System (SRS) Algorithm Reference

## Overview

This document provides technical details for implementing the Spaced Memory-2 (SM-2) algorithm with research-based modifications from the Cepeda et al. (2006) meta-analysis of optimal spacing intervals. The SM-2 algorithm is the foundation of nearly all modern spaced repetition systems (Anki, SuperMemo, Mnemosyne, etc.) and has been empirically validated across thousands of learning studies.

## Historical Context: Development of Spaced Repetition

### Ebbinghaus Forgetting Curve (1885)
Hermann Ebbinghaus, pioneer of experimental learning science, discovered that forgetting follows an exponential decay pattern: the more you review material, the slower you forget it. He demonstrated that reviewing at optimal intervals (when you're just about to forget) maximizes long-term retention.

### Bjork's Desirable Difficulty Theory (1994)
Robert Bjork proposed that learning requires "desirable difficulty": encoding conditions that feel challenging during learning but produce better long-term retention than easy, fluent encoding. This theory explains why cramming feels productive (high fluency during learning) but produces poor retention (low long-term performance).

### Wozniak's SM-2 Algorithm (1990)
Piotr Wozniak created the SuperMemo system and developed the SM-2 algorithm, implementing Ebbinghaus's forgetting curve empirically. SM-2 uses quality-of-response (rated 0-5) to dynamically adjust spacing intervals and an "ease factor" parameter to personalize spacing to each learner's memory strength.

### Cepeda Meta-Analysis (2006)
Cepeda et al. conducted a meta-analysis of 317 experiments examining optimal spacing intervals across diverse learners and materials. Key finding: **retention is optimal when the interval between study sessions is 10-20% of the desired retention interval**.

For example:
- If you want to retain material for 1 month: optimal review interval = 3-6 days
- If you want to retain material for 1 year: optimal review interval = 37-73 days
- If you want to retain material for 5 years: optimal review interval = 180-365 days

This principle is integrated into the SM-2 modifications below.

## SM-2 Algorithm Specification

### Parameters

Each word in the vocabulary database maintains the following parameters:

```
interval_days: integer ≥ 1
  The number of days until the next scheduled review
  Default for new words: 1 day

ease_factor: float (minimum 1.3, typical range 1.3-2.8)
  Multiplier controlling how quickly intervals grow
  High ease_factor (2.5+): memory is strong; intervals grow quickly
  Low ease_factor (1.3-1.5): memory is weak; intervals grow slowly
  Default for new words: 2.5

next_review: date
  The date when the word should next appear in review session
  Calculated as: today + interval_days

review_count: integer ≥ 0
  Total number of times this word has been reviewed

correct_count: integer ≥ 0
  Number of times learner correctly recalled the word

incorrect_count: integer ≥ 0
  Number of times learner failed to correctly recall the word

status: string ∈ {"new", "learning", "relearning", "mastered"}
  Tracks word's current position in acquisition curve
  new: never reviewed
  learning: interval < 30 days (still acquiring)
  relearning: recently failed (interval reset to 1 day)
  mastered: interval > 120 days AND correct_count > 3
```

### SM-2 Update Algorithm

After each review, the algorithm updates interval_days, ease_factor, and status based on the learner's response quality rating.

#### Quality Rating Scale

Present learner with four options (or collect quality rating 1-5):

```
[Easy]     "I knew this immediately"        → quality = 5
[Good]     "I remembered correctly"         → quality = 4
[Hard]     "I barely remembered"            → quality = 3
[Forgot]   "I completely forgot"            → quality = 1
```

Why this scale: Research on confidence judgments shows that learner self-assessments of recall quality correlate 0.7-0.8 with actual long-term retention (Dunlosky & Metcalfe, 2009). Simplifying to 4 categories improves reliability compared to the original SM-2's 0-5 scale.

#### Algorithm Logic

```pseudocode
function updateSRS(word, quality):
    // Increment review counter
    word.review_count = word.review_count + 1

    // Update ease factor based on quality
    if quality >= 3:  // Correct recall
        word.correct_count = word.correct_count + 1

        if quality == 5:  // Easy recall
            word.ease_factor = word.ease_factor + 0.15
        elif quality == 4:  // Good recall
            word.ease_factor = word.ease_factor  // No change
        elif quality == 3:  // Hard recall
            word.ease_factor = word.ease_factor - 0.05

    else:  // Incorrect recall (quality < 3)
        word.incorrect_count = word.incorrect_count + 1
        word.ease_factor = max(1.3, word.ease_factor - 0.2)
        word.status = "relearning"

    // Update interval based on quality
    if word.review_count == 1:
        // First review: always schedule for 1 day
        word.interval_days = 1

    elif word.review_count == 2:
        // Second review: schedule for 3 days (Ebbinghaus: optimal second interval is ~3 days)
        word.interval_days = 3

    else:
        // Subsequent reviews
        if quality >= 3:  // Correct
            word.interval_days = round(word.interval_days * word.ease_factor)
        else:  // Incorrect
            word.interval_days = 1

    // Ensure minimum interval of 1 day
    word.interval_days = max(1, word.interval_days)

    // Update mastery status
    if word.interval_days > 120 AND word.correct_count > 3:
        word.status = "mastered"
    elif word.interval_days >= 30:
        word.status = "learning"
    elif word.status == "relearning":
        word.status = "relearning"  // Remains in relearning until interval ≥ 30
    else:
        word.status = "learning"

    // Calculate next review date
    word.next_review = today + word.interval_days

    return word
```

### Worked Example

Word: "hablar" (Spanish: to speak)

**Initial state (new word):**
```
interval_days: 1
ease_factor: 2.5
next_review: 2026-03-25
review_count: 0
correct_count: 0
status: "new"
```

**Review 1 (2026-03-25): Learner rates "Good" (quality=4)**
```
review_count = 1
correct_count = 1
ease_factor = 2.5 (no change for quality=4)
interval_days = 1 (first review always 1 day)
next_review = 2026-03-26
status = "learning"
```

**Review 2 (2026-03-26): Learner rates "Easy" (quality=5)**
```
review_count = 2
correct_count = 2
ease_factor = 2.5 + 0.15 = 2.65 (increased for quality=5)
interval_days = 3 (second review always 3 days)
next_review = 2026-03-29
status = "learning"
```

**Review 3 (2026-03-29): Learner rates "Good" (quality=4)**
```
review_count = 3
correct_count = 3
ease_factor = 2.65 (no change)
interval_days = round(3 × 2.65) = 8 (rounded from 7.95)
next_review = 2026-04-06
status = "learning"
```

**Review 4 (2026-04-06): Learner rates "Forgot" (quality=1)**
```
review_count = 4
incorrect_count = 1
ease_factor = max(1.3, 2.65 - 0.2) = 2.45
interval_days = 1 (reset on incorrect)
next_review = 2026-04-07
status = "relearning"
```

**Review 5 (2026-04-07): Learner rates "Good" (quality=4)**
```
review_count = 5
correct_count = 4
ease_factor = 2.45
interval_days = round(1 × 2.45) = 2
next_review = 2026-04-09
status = "learning"
```

This example shows how ease_factor personalizes spacing to the learner's performance: after the forgotten item is relearned, the next interval is 2 days (shorter than the pre-forgetting interval of 8 days), reflecting the learner's lower ease_factor.

## Optimal Spacing Intervals: Cepeda et al. (2006) Meta-Analysis

### Key Finding: The 10-20% Rule

Analysis of 317 spacing experiments revealed: **retention is optimal when the interval between successive study sessions equals 10-20% of the desired retention interval**.

#### Application Examples

**Retention goal: 1 month**
- Desired retention interval: 30 days
- Optimal study intervals: 3-6 days
- SM-2 produces this naturally: interval sequence 1d → 3d → 8d (within range)

**Retention goal: 1 year (12 months)**
- Desired retention interval: 365 days
- Optimal study intervals: 37-73 days
- SM-2 produces: 1d → 3d → 8d → 21d → 55d → 147d
- Note: 55 days falls within optimal range; 147 days exceeds for 1-year retention goal

**Retention goal: 5 years (60 months)**
- Desired retention interval: 1825 days
- Optimal study intervals: 183-365 days
- SM-2 produces: natural progression reaches this range by 6-7th review

### Lag Effect: Implications for Vocabulary Learning

The meta-analysis also examined the "lag effect": how the total number of study sessions affects retention. Key findings:

- **Increasing lags (longer intervals between sessions) with each successive review improves retention**
- 2 spaced sessions ≈ 2× better retention than 1 session
- 3 spaced sessions ≈ 3.5× better retention than 1 session
- 4+ sessions show diminishing returns but still produce superior retention

Implication: For vocabulary mastery, aim for minimum 3-4 spaced reviews per word before considering it "mastered" (retention interval > 120 days).

### Moderating Variables: When SM-2 Requires Adjustment

The Cepeda meta-analysis identified variables that moderate optimal spacing:

#### 1. Retention Interval (already covered: 10-20% rule)

#### 2. Learner Age
- **Young children (< 8 years)**: Optimal spacing is shorter (tighter review schedule)
- **Adults**: Standard SM-2 intervals apply
- **Older adults (> 65 years)**: May benefit from slightly shorter intervals

For language learning: Most adult learners; apply standard SM-2.

#### 3. Learner Ability / Prior Knowledge
- **High-ability learners**: Can tolerate longer intervals; ease_factor naturally increases
- **Low-ability learners**: Need shorter intervals; ease_factor naturally decreases
- **Advanced learners** (B2+): Can use longer intervals; reduce review_count requirement for mastery to 2
- **Beginner learners** (A1): Require more reviews; increase review_count requirement for mastery to 4-5

SM-2 handles this automatically via ease_factor adjustment.

#### 4. Material Difficulty
- **Easy material** (cognates, high-frequency words): ease_factor increases; learners reach longer intervals faster
- **Difficult material** (non-cognates, abstract concepts): ease_factor decreases; learners stay in learning phase longer

SM-2 handles this automatically based on learner's actual performance.

#### 5. Type of Learning Goal
- **Recognition** (learner must identify word given definition): shorter intervals work well
- **Production** (learner must generate word; speaking/writing): longer intervals required
- **Flexible production** (use word appropriately in context): longest intervals

For vocabulary learning: Prioritize production exercises; use longer intervals (120+ days) only after consistent correct production (correct_count ≥ 3).

#### 6. Inter-Study Interval Variability
- **Fixed intervals** (review every exactly 3 days): less effective
- **Variable intervals** (review at 2-4 day intervals): more effective (variability aids transfer)

SM-2 naturally produces variable intervals via ease_factor multiplication.

## Frequency List Guidance by Language

High-frequency vocabulary should be mastered before advancing to less frequent words. The following guidance applies across all languages:

### Frequency Band: Top 100 Words

**Coverage**: ~45-50% of everyday conversation
**CEFR Level**: A1 (Beginner)
**Characteristics**: Articles, pronouns, common verbs (be, have, do), high-frequency nouns (person, time, place), prepositions
**Time to mastery**: 2-4 weeks with daily review
**Example Spanish Top 100**: el, la, de, que, y, a, en, un, ser, se, no, haber, por, con, su, para, es, uno, pero, lo

**Strategy**:
- Master top 100 completely before advancing to top 500
- Use frequency lists from reliable corpus sources (not commercial apps)
- Recommended review frequency: daily until mastery (interval reaches 30+ days)

### Frequency Band: Top 500 Words

**Coverage**: ~70-75% of everyday conversation
**CEFR Level**: A2 (Elementary)
**Characteristics**: Adjectives, additional verbs, nouns describing common experiences
**Time to mastery**: 6-12 weeks with daily review
**Example Spanish Top 500 includes**: hacer, ir, tiempo, persona, día, año, hombre, mujer, vida, etc.

**Strategy**:
- Begin learning top 500 only after top 100 reaches 80%+ mastery
- Use interleaved practice: mix top 100 maintenance reviews with top 500 learning
- Review frequency: 3-5× per week, progressing to weekly as interval increases

### Frequency Band: Top 1000 Words

**Coverage**: ~80% of everyday conversation (Paul Nation's benchmark)
**CEFR Level**: B1 (Intermediate)
**Characteristics**: Specialized verbs (think, know, say), descriptive adjectives, nouns for abstract concepts
**Time to mastery**: 3-6 months with consistent study
**Example Spanish Top 1000 includes**: saber, decir, pensar, creer, parecer, sentir, mundo, momento, caso, etc.

**Strategy**:
- Top 1000 mastery should be primary goal for all learners
- Once top 1000 is mastered (average interval > 60 days), learners can conduct independent communication with effort
- Use 80/20 principle: spend 80% of time on top 1000; only 20% on specialized vocabulary

### Frequency Band: Top 3000 Words

**Coverage**: ~89% of conversation
**CEFR Level**: B2 (Upper Intermediate)
**Characteristics**: Technical vocabulary, less common verbs, specialized nouns
**Time to mastery**: 6-12 months
**Strategy**: Begin after top 1000 reaches 80%+ mastery

### Frequency Band: Top 5000 Words

**Coverage**: ~93% of conversation
**CEFR Level**: C1 (Advanced)
**Time to mastery**: 12-24 months
**Strategy**: Begin after top 3000 mastery

### Frequency Band: 5000+ Words (Specialized/Academic)

**Coverage**: 93%+ (with diminishing returns)
**CEFR Level**: C2 (Mastery)
**Time to mastery**: Variable (3+ years depending on specialization)
**Strategy**: Focus on domain-specific words (business, academic, technical) relevant to learner's goals

## Frequency List Sources by Language

Reliable, evidence-based frequency lists for vocabulary planning:

### Spanish
- **Frequency Dictionary of Spanish** (Mark Davies)
  - 5000 most frequent words with context
  - Corpus-based on 500+ million word Spanish corpus
  - Frequency rankings from Spanish National Corpus
  - Recommended: Use top 1000 as primary mastery target

- **CEF Level Frequency Bands** (Instituto Cervantes)
  - Official CEFR frequency guidelines for Spanish
  - A1: ~600 words, A2: ~1200 words, B1: ~2000 words, B2: ~3500 words

### French
- **Frequency Dictionary of French** (Mark Davies)
  - Similar corpus-based approach as Spanish
  - Top 1000 covers ~78% of conversational French

- **COCOON Corpus** (CNRS, France)
  - Modern French frequency data
  - Includes genre-specific frequencies (spoken vs. written)

### German
- **Frequency Dictionary of German** (Mark Davies)
  - Top 1000 covers ~78% of German conversation
  - Separates spoken/written frequencies

- **DWDS Corpus** (German Academy of Sciences)
  - Modern, regularly updated German word frequency

### Portuguese
- **Frequency Dictionary of Portuguese** (Mark Davies)
  - Separate data for Brazilian and European Portuguese
  - Top 1000 covers ~80% of conversation

### Italian
- **Frequency Dictionary of Italian** (Mark Davies)
  - Corpus-based from 1 billion word Italian corpus
  - Top 1000 covers ~79% of conversation

### Russian / Cyrillic Languages
- **Russian Frequency Dictionary** (various sources)
  - Top 1000 Russian words (Cyrillic script)
  - Note: Russian has more complex morphology; "top 1000 words" may have 5000+ inflected forms

### Mandarin Chinese / CJK Languages
- **Modern Chinese Word List** (HSK Official)
  - HSK levels 1-6 correspond approximately to A1-B2
  - Top 1000 most frequent Mandarin words
  - Note: CJK scripts require character-based frequency analysis, not word-based

### General Guideline: Choosing Frequency Sources
1. **Corpus-based > anecdotal**: Use frequency derived from large text corpora (100M+ words), not subjective lists
2. **Recent > dated**: Prefer frequency lists updated in last 5 years (language evolves; internet words matter now)
3. **Genre-specific > general**: If learner has specific goals (business, medical, academic), use specialized frequency lists
4. **Official standards**: For CEFR-aligned learning, use official frequency guidelines from standardization bodies (Instituto Cervantes, GOETHE Institut, etc.)

## Practical Implementation Recommendations

### For New Learners (A1-A2)
1. Start with top 100 words using frequent daily reviews (5-7× per week)
2. Review interval progression: 1d → 3d → 7d, stop progression at 7 days for security
3. Keep ease_factor lower (1.5-2.0 range) via conservative assessment (quality 3-4 rating)
4. Add new words at rate of 5-10 per week; prioritize over longer intervals
5. Use all exercise types but emphasize recognition (MC) > production (translation) initially

### For Intermediate Learners (B1-B2)
1. Maintain top 1000 words with weekly reviews
2. Allow interval progression: 1d → 3d → 7d → 14d → 30d → 60d → 120d
3. Target ease_factor 2.2-2.6 range (reflecting stronger memory)
4. Add 10-20 new words per week; begin specialized vocabulary
5. Emphasize production exercises (translation, speaking, writing)
6. Begin spaced reading (immersion materials) to reinforce vocabulary in context

### For Advanced Learners (C1+)
1. Maintenance reviews for top 1000 words at 2-4 week intervals
2. Aggressive interval growth: ease_factor 2.5-2.8; intervals reach 120+ days quickly
3. Focus on specialized vocabulary for learner's goals (business, academic, literary, etc.)
4. Reduce review_count requirement for mastery to 2-3 (confidence in assessment)
5. Prioritize production, context-driven exercises exclusively
6. Integrate vocabulary into immersion materials (novels, podcasts, professional texts)

## Algorithm Edge Cases and Handling

### Edge Case 1: Learner Rates Quality Inconsistently
**Symptom**: Learner sometimes rates words "Easy" immediately after forgetting them
**Cause**: Learner overconfidence or misunderstanding of quality scale
**Handling**:
- Re-explain quality scale: "Easy = knew instantly without thinking"
- If ease_factor goes above 2.8, cap it: `ease_factor = min(2.8, ease_factor)`
- Add explicit calibration check: after 5 ratings, show learner accuracy vs. self-assessed quality

### Edge Case 2: Ease Factor Drops Below 1.3
**Symptom**: Word is consistently forgotten; ease_factor approaching 1.0
**Cause**: Word is genuinely difficult; learner hasn't encoded it well
**Handling**:
- Check mnemonic and context: is the mnemonic vivid? Are examples clear?
- Recommend learner create their own mnemonic or look up etymological connection
- If ease_factor < 1.3 for 5+ reviews, consider removing word from learning set; offer to revisit later
- Do not force continued learning of words with ease_factor < 1.3 (diminishing returns)

### Edge Case 3: Interval Exceeds 365 Days
**Symptom**: Word reaches interval of 1+ year
**Cause**: Word learned very well; high ease_factor compounded over many reviews
**Handling**:
- Cap interval at 365 days: `interval_days = min(365, interval_days)`
- Mark status as "mastered" after 120 days + correct_count > 3
- For truly mastered words (>1 year interval), move to "hibernation" status
- Offer learner option: retire word from active learning or maintain at annual review

### Edge Case 4: New Learner Has Very Large Vocabulary
**Symptom**: Learner imports 1000+ words at once for review
**Cause**: Learner imported a list without filtering by proficiency level
**Handling**:
- Check CEFR level of imported words; warn if mismatch with learner's level
- Recommend filtering: "These words are C1 level. Your profile is B1. Start with B1 words first?"
- Limit new words per session to 20 (cognitive load limits)
- Spread import across multiple sessions

### Edge Case 5: Vocabulary List Is Stale
**Symptom**: next_review date is far in the past; learner hasn't reviewed in months
**Cause**: Learner took extended break from language learning
**Handling**:
- Reset all intervals to 1 day (fresh start)
- Set status to "relearning" for all words
- Inform learner: "Your vocabulary needs refreshing. These words are due for review today. Let's reactivate your learning!"
- Do NOT penalize learner for break; treat as natural forgetting curve recovery

## Summary: SM-2 Algorithm Key Parameters

For quick reference during implementation:

| Parameter | Initial Value | Range | Notes |
|-----------|---------------|-------|-------|
| interval_days | 1 | 1-365 | Capped at 365; minimum 1 |
| ease_factor | 2.5 | 1.3-2.8 | Capped 1.3 (min) and 2.8 (max) |
| next_review | today + 1 | future dates | Always ≥ today |
| review_count | 0 | 0+ | Increments after each review |
| correct_count | 0 | 0-review_count | Must be ≤ review_count |
| status | "new" | {new, learning, relearning, mastered} | Transitions: new→learning or relearning; relearning→learning; learning→mastered |

This reference should be consulted during algorithm implementation to ensure SM-2 is correctly applied, and during troubleshooting if review behavior seems incorrect.
