from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def control_keyboard(voice_enabled: bool, deep_enabled: bool, coder_enabled: bool) -> InlineKeyboardMarkup:
    """Build an inline keyboard for toggling modes.

    The button label reflects the current state and the callback data
    is a generic ``*_toggle`` identifier that handlers can interpret.
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"Voice {'Off' if voice_enabled else 'On'}",
                    callback_data="voice_toggle",
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"Deep {'Off' if deep_enabled else 'On'}",
                    callback_data="deep_toggle",
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"Coder {'Off' if coder_enabled else 'On'}",
                    callback_data="coder_toggle",
                )
            ],
        ]
    )
