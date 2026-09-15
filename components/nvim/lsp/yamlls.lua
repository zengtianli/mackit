return {
  cmd = { 'yaml-language-server', '--stdio' },
  filetypes = { 'yaml', 'yaml.docker-compose' },
  root_markers = { '.git' },
  settings = {
    redhat = { telemetry = { enabled = false } },
    yaml = {
      schemaStore = { enable = false },
      validate = false,
      customTags = {
        "!fn", "!And", "!If", "!Not", "!Equals", "!Or", "!FindInMap sequence",
        "!Base64", "!Cidr", "!Ref", "!Sub", "!GetAtt", "!GetAZs",
        "!ImportValue", "!Select", "!Split", "!Join sequence"
      }
    }
  }
}
