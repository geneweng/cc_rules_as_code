# Rules as Code

A survey of **Rules as Code (RaC)** — the practice of publishing an official, machine-executable version of legislation, regulation, and policy alongside the natural-language text — with particular attention to the opportunities (and risks) that AI and large language models bring to the field.

## Contents

| File | Description |
|---|---|
| [`rules-as-code-survey.md`](rules-as-code-survey.md) | The survey in Markdown, with ~30 linked sources |
| [`rules-as-code-survey.pdf`](rules-as-code-survey.pdf) | The same survey rendered as a PDF |

## What's covered

1. **What Rules as Code is** — definition, core claims, and the OECD "Cracking the Code" framing
2. **Origins and global landscape** — New Zealand (Better Rules), France (OpenFisca), NSW Australia, Canada (Blawx), Jersey, and U.S. public-benefits work
3. **Tools and technical approaches** — microsimulation libraries, logic programming, and legal DSLs (Catala)
4. **Standing challenges** — open texture and discretion, interpretation authority, encoding cost, accountability
5. **The AI opportunity** — the survey's focus:
   - LLMs as encoders (policy-to-code translation, e.g. the Beeck Center's Policy2Code experiments)
   - Neurosymbolic hybrids: LLMs at the language edges, verified rule engines at the core
   - AI as verifier and legislative drafting copilot
   - Conversational interfaces backed by authoritative encodings
   - New risks: plausible-but-wrong encodings, laundered interpretation, over-encoding discretion
6. **Outlook** — why AI strengthens, rather than replaces, the case for Rules as Code

## Regenerating the PDF

```sh
pandoc rules-as-code-survey.md -o rules-as-code-survey.pdf \
  --pdf-engine=xelatex -V mainfont="Helvetica" -V geometry:margin=1in \
  -V colorlinks=true -V linkcolor=blue -V urlcolor=blue \
  --metadata title="Rules as Code: A Survey" --metadata date="July 2026"
```

---

*Compiled July 2026 from public web sources; see the Sources section of the survey for the full reference list.*
