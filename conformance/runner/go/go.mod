module github.com/changespec/changespec/conformance/runner/go

go 1.22

require (
	github.com/changespec/changespec-go v0.0.0
	gopkg.in/yaml.v3 v3.0.1
)

require (
	github.com/santhosh-tekuri/jsonschema/v6 v6.0.1 // indirect
	golang.org/x/text v0.14.0 // indirect
)

replace github.com/changespec/changespec-go => ../../../reference/go
