# Changelog

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


[unreleased]: https://github.com/simplebot-org/simplebot/compare/v1.1.0...HEAD

[1.1.0]: https://github.com/simplebot-org/simplebot/compare/v1.0.1...v1.1.0

[1.0.1]: https://github.com/simplebot-org/simplebot/compare/v0.10.0...v1.0.1
