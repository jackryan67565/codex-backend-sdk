"""OpenAI-shaped prompt-caching example for a stable prefix and changing suffix."""

from codex_backend_sdk import OpenAI


STABLE_REFERENCE = """
Place stable instructions, tools, schemas, examples, and reference material here.
For GPT-5.6 and later, the reusable visible prefix must be at least 1,024 tokens.
""".strip()


def main() -> None:
    with OpenAI(max_retries=0).authenticate() as client:
        for question in (
            "Apply the reference to case A.",
            "Apply the reference to case B.",
        ):
            response = client.responses.create(
                input=[
                    {
                        "role": "developer",
                        "content": [{
                            "type": "input_text",
                            "text": STABLE_REFERENCE,
                            "prompt_cache_breakpoint": {"mode": "explicit"},
                        }],
                    },
                    {"role": "user", "content": question},
                ],
                prompt_cache_key="example:stable-reference:v1",
                prompt_cache_options={"mode": "explicit", "ttl": "30m"},
                store=False,
            )

            details = response.usage.input_tokens_details if response.usage else None
            input_tokens = response.usage.input_tokens if response.usage else None
            cached_tokens = details.cached_tokens if details else None
            cache_write_tokens = details.cache_write_tokens if details else None
            ordinary_tokens = None
            if None not in (input_tokens, cached_tokens, cache_write_tokens):
                ordinary_tokens = input_tokens - cached_tokens - cache_write_tokens
            print({
                "input_tokens": input_tokens,
                "cached_tokens": cached_tokens,
                "cache_write_tokens": cache_write_tokens,
                "ordinary_input_tokens": ordinary_tokens,
            })


if __name__ == "__main__":
    main()
