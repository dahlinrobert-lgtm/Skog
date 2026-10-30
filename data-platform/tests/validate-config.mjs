import { readFileSync } from "node:fs";
import { spawnSync } from "node:child_process";

const paths = ["data-platform/config/sources.yml", "data-platform/config/model-contract.yml"];
const ruby = String.raw`
require "yaml"
paths = ARGV
paths.each do |path|
  value = YAML.safe_load_file(path, permitted_classes: [], aliases: false)
  raise "#{path}: root must be a mapping" unless value.is_a?(Hash)
  raise "#{path}: schema_version must be 1" unless value["schema_version"] == 1
end
sources = YAML.safe_load_file(paths[0], permitted_classes: [], aliases: false)
ids = sources.fetch("sources").map { |source| source.fetch("source_id") }
raise "source_id values must be unique" unless ids.uniq.length == ids.length
sources.fetch("sources").each do |source|
  %w[source_id name source_type provider access_method connector status cadence geography format].each do |key|
    raise "#{source["source_id"]}: missing #{key}" if source[key].nil?
  end
end
model = YAML.safe_load_file(paths[1], permitted_classes: [], aliases: false)
raise "common_fields missing" unless model["common_fields"].is_a?(Hash)
raise "record_types missing" unless model["record_types"].is_a?(Hash) && !model["record_types"].empty?
puts "Validated #{ids.length} source definitions and #{model["record_types"].length} record types."
`;
const result = spawnSync("ruby", ["-e", ruby, ...paths], { encoding: "utf8" });
if (result.status !== 0) {
  process.stderr.write(result.stderr || result.stdout || "YAML validation failed\n");
  process.exit(result.status ?? 1);
}
process.stdout.write(result.stdout);
