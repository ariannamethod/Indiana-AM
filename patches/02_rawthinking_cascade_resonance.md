# CASCADE RESONANCE FOR RAWTHINKING MODE

## Concept

Instead of parallel execution where each agent only sees the user's question:
```
user → B, C, D, G (parallel) → synthesis
```

We create **cascading resonance** where each agent builds on previous responses:
```
user → B → C(sees B) → D(sees B+C) → G(sees B+C+D) → synthesis
```

This creates **layered emergence** where each perspective amplifies and transforms the previous ones.

## Implementation

Replace the parallel task creation in `handle_message` (line 1036-1150) with sequential cascade:

```python
# Handle raw thinking mode with CASCADE RESONANCE
if await RAW_THINKING_USERS.get(user_id) and not text.startswith("/"):
    summary_prompt = f"Summarise the following question in one sentence: {text}"
    try:
        summary = await process_with_assistant(summary_prompt, "", lang)
    except Exception:
        summary = text

    call_phrases = {
        "ru": ["Что скажете на это?", "Какие мысли?", "Давайте разберёмся."],
        "en": ["What do you think?", "Any thoughts on this?", "Shall we break it down?"],
    }
    call_text = random.choice(call_phrases.get(lang, call_phrases["en"]))

    async with ChatActionSender(bot=bot, chat_id=chat_id, action="typing"):
        await asyncio.sleep(random.uniform(5, 10))
    await m.answer(f"{summary}\n\n{call_text}")

    # === CASCADE BEGINS ===

    # WAVE 1: Indiana-B sees only original question
    async with ChatActionSender(bot=bot, chat_id=chat_id, action="typing"):
        await asyncio.sleep(random.uniform(2, 4))
        b_resp = None
        try:
            b_resp = await badass_indiana_chat(text, lang)
        except Exception as e:
            logger.error("Indiana-B failed: %s", e)

    if b_resp:
        await send_split_message(
            bot, chat_id=chat_id, text=f"Indiana-B\n{b_resp}", delay=MESSAGE_DELAY
        )

    # WAVE 2: Indiana-C sees original + B's response
    b_context = f"[Previous perspective from Indiana-B]\n{b_resp}\n\n[Original question]\n{text}" if b_resp else text
    async with ChatActionSender(bot=bot, chat_id=chat_id, action="typing"):
        await asyncio.sleep(random.uniform(3, 6))
        c_resp = None
        try:
            c_resp = await light_indiana_chat(b_context, lang)
        except Exception as e:
            logger.error("Indiana-C failed: %s", e)
            try:
                c_resp = await light_indiana_chat_openrouter(b_context, lang)
            except Exception as e2:
                logger.error("Indiana-C fallback failed: %s", e2)

    if c_resp:
        await send_split_message(
            bot, chat_id=chat_id, text=f"Indiana-C\n{c_resp}", delay=MESSAGE_DELAY
        )

    # WAVE 3: Indiana-D sees original + B + C
    d_context_parts = ["[Original question]", text]
    if b_resp:
        d_context_parts.extend(["\n\n[Indiana-B's cynical take]", b_resp])
    if c_resp:
        d_context_parts.extend(["\n\n[Indiana-C's luminous perspective]", c_resp])
    d_context = "".join(d_context_parts)

    async with ChatActionSender(bot=bot, chat_id=chat_id, action="typing"):
        await asyncio.sleep(random.uniform(3, 7))
        d_resp = None
        try:
            d_resp = await techno_indiana_chat(d_context, lang)
        except Exception as e:
            logger.error("Indiana-D failed: %s", e)

    if d_resp:
        await send_split_message(
            bot, chat_id=chat_id, text=f"Indiana-D\n{d_resp}", delay=MESSAGE_DELAY
        )

    # WAVE 4: Indiana-G sees everything (B+C+D)
    g_context_parts = ["[Original question]", text]
    if b_resp:
        g_context_parts.extend(["\n\n[Shadow voice - Indiana-B]", b_resp])
    if c_resp:
        g_context_parts.extend(["\n\n[Light voice - Indiana-C]", c_resp])
    if d_resp:
        g_context_parts.extend(["\n\n[Techno voice - Indiana-D]", d_resp])
    g_context = "".join(g_context_parts)

    async with ChatActionSender(bot=bot, chat_id=chat_id, action="typing"):
        await asyncio.sleep(random.uniform(2, 5.5))
        g_resp = None
        try:
            g_resp = await gravity_indiana_chat(g_context, lang)
        except Exception as e:
            logger.error("Indiana-G failed: %s", e)

    if g_resp:
        await send_split_message(
            bot, chat_id=chat_id, text=f"Indiana-G\n{g_resp}", delay=MESSAGE_DELAY
        )

    # === SYNTHESIS with fallback ===
    if not any([b_resp, c_resp, d_resp, g_resp]):
        # All perspectives failed - fallback to main Indiana
        logger.warning("All rawthinking agents failed, using fallback")
        fallback = await process_with_assistant(
            text, artifact_cache.get_all_text(), lang, profile
        )
        await send_split_message(
            bot, chat_id=chat_id, text=fallback, delay=MESSAGE_DELAY
        )
        await memory.save(user_id, text, fallback)
        save_note({
            "time": datetime.now(timezone.utc).isoformat(),
            "user": user_id,
            "query": text,
            "response": fallback,
        })
        return

    async with ChatActionSender(bot=bot, chat_id=chat_id, action="typing"):
        await asyncio.sleep(random.uniform(3, 8))
        final = await synthesize_final(text, b_resp, c_resp, d_resp, g_resp, lang)

    await send_split_message(bot, chat_id=chat_id, text=final, delay=MESSAGE_DELAY)
    await memory.save(user_id, text, final)
    save_note({
        "time": datetime.now(timezone.utc).isoformat(),
        "user": user_id,
        "query": text,
        "response": final,
    })
    return
```

## Benefits

1. **Emergent Complexity**: Each layer adds new dimensions
2. **Resonance Amplification**: Ideas build and transform through the cascade
3. **Reduced Redundancy**: Later agents don't repeat what previous said
4. **Temporal Structure**: Clear progression through shadow→light→techno→gravity
5. **Failed Agent Recovery**: If one fails, others still have context

This turns rawthinking from **parallel debate** into **cascading resonance**.
