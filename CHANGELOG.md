# Changelog

## [2.2.0]

- show shield badge in commands/filters for bot administrators.
- make commands case insensitive, now `/Help` is equivalent to `/help`.

## [2.1.1]

- mark messages as read before processing them.

## [2.1.0]

- mark messages as read so MDN work, if enabled.

## [2.0.0]

- ignore messages from other bots using the new Delta Chat API. Added `deltabot_incoming_bot_message` hook to process messages from bots.
- allow to get account configuration values with `set_config` command.
- allow to register administrators-only filters.
- send bot's help as HTML message.
- disable "move to DeltaChat folder" (mvbox_move setting) by default.
- log less info if not in "debug" mode.
- help command now also includes filters descriptions.
- **breaking change:** plugins must register their "user preferences" with `DeltaBot.add_preference()` then the setting will be available to users with `/set` command.
- **breaking change:** improved command and filter registration.
- **breaking change:** changed configuration folder to `~/.simplebot`

## [1.1.1]

- fix bug in `simplebot.utils.get_default_account()` (#72)

## [1.1.0]

- Improved pytestplugin to allow simulating incoming messages with encryption errors (#68)

## [1.0.1]

- **From upstream:** major rewrite of deltabot to use new deltachat core python bindings
  which are pluginized themselves.
- Changed SimpleBot logo (thanks Dann) and added default avatar
  generation based on account color.
- Added `@simplebot.command` and `@simplebot.filter` decorators to
  simplify commands and filters creation.
- Added new hooks `deltabot_ban`, `deltabot_unban`,
  `deltabot_title_changed` and `deltabot_image_changed`
- Added options to influence filter execution order.
- Added support for commands that are available only to bot administrators.
- Improved command line, added account manager, administrator tools,
  options to set avatar, display name, status and other low level
  settings for non-standard servers.
- Added default status message.
- Improved code readability with type hints.

## 0.10.0

- initial release


[Unreleased]: https://github.com/simplebot-org/simplebot/compare/v2.2.0...HEAD

[2.2.0]: https://github.com/simplebot-org/simplebot/compare/v2.1.1...v2.2.0

[2.1.1]: https://github.com/simplebot-org/simplebot/compare/v2.1.0...v2.1.1

[2.1.0]: https://github.com/simplebot-org/simplebot/compare/v2.0.0...v2.1.0

[2.0.0]: https://github.com/simplebot-org/simplebot/compare/v1.1.1...v2.0.0

[1.1.1]: https://github.com/simplebot-org/simplebot/compare/v1.1.0...v1.1.1

[1.1.0]: https://github.com/simplebot-org/simplebot/compare/v1.0.1...v1.1.0

[1.0.1]: https://github.com/simplebot-org/simplebot/compare/v0.10.0...v1.0.1
