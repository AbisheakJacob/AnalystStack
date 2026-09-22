# Graph Report - AnalystStack  (2026-09-01)

## Corpus Check
- 108 files · ~39,944 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1054 nodes · 1527 edges · 94 communities (68 shown, 26 thin omitted)
- Extraction: 74% EXTRACTED · 26% INFERRED · 0% AMBIGUOUS · INFERRED: 393 edges (avg confidence: 0.64)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `134b045f`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- [[_COMMUNITY_Graphify Skill & Exports|Graphify Skill & Exports]]
- [[_COMMUNITY_BigQuery Manager Layer|BigQuery Manager Layer]]
- [[_COMMUNITY_Data IO ReadWrite|Data IO Read/Write]]
- [[_COMMUNITY_Connector Facade & Base Contract|Connector Facade & Base Contract]]
- [[_COMMUNITY_AnalystStack Docs & Roadmap|AnalystStack Docs & Roadmap]]
- [[_COMMUNITY_Settings & Error Handling|Settings & Error Handling]]
- [[_COMMUNITY_Format CLI|Format CLI]]
- [[_COMMUNITY_Code Formatters (PythonSQL)|Code Formatters (Python/SQL)]]
- [[_COMMUNITY_Client Wrappers (Auth)|Client Wrappers (Auth)]]
- [[_COMMUNITY_BigQuery Connector Tests|BigQuery Connector Tests]]
- [[_COMMUNITY_DataReader Tests|DataReader Tests]]
- [[_COMMUNITY_DataWriter Tests|DataWriter Tests]]
- [[_COMMUNITY_Python Formatter Tests|Python Formatter Tests]]
- [[_COMMUNITY_Excel Cell Parsing|Excel Cell Parsing]]
- [[_COMMUNITY_Metadata Extraction|Metadata Extraction]]
- [[_COMMUNITY_Test Fixtures|Test Fixtures]]
- [[_COMMUNITY_BigQuery Table ID Utils|BigQuery Table ID Utils]]
- [[_COMMUNITY_Logging|Logging]]
- [[_COMMUNITY_Package Init|Package Init]]
- [[_COMMUNITY_Docs Build Workflow|Docs Build Workflow]]
- [[_COMMUNITY_Graphify Knowledge Graph|Graphify Knowledge Graph]]
- [[_COMMUNITY_Connectors Init|Connectors Init]]
- [[_COMMUNITY_Token Reduction Benchmark|Token Reduction Benchmark]]
- [[_COMMUNITY_GraphML Export|GraphML Export]]
- [[_COMMUNITY_SVG Export|SVG Export]]
- [[_COMMUNITY_Audit Trail|Audit Trail]]
- [[_COMMUNITY_Community 26|Community 26]]
- [[_COMMUNITY_Community 27|Community 27]]
- [[_COMMUNITY_Community 28|Community 28]]
- [[_COMMUNITY_Community 29|Community 29]]
- [[_COMMUNITY_Community 30|Community 30]]
- [[_COMMUNITY_Community 31|Community 31]]
- [[_COMMUNITY_Community 32|Community 32]]
- [[_COMMUNITY_Community 33|Community 33]]
- [[_COMMUNITY_Community 34|Community 34]]
- [[_COMMUNITY_Community 35|Community 35]]
- [[_COMMUNITY_Community 36|Community 36]]
- [[_COMMUNITY_Community 37|Community 37]]
- [[_COMMUNITY_Community 38|Community 38]]
- [[_COMMUNITY_Community 39|Community 39]]
- [[_COMMUNITY_Community 40|Community 40]]
- [[_COMMUNITY_Community 41|Community 41]]
- [[_COMMUNITY_Community 42|Community 42]]
- [[_COMMUNITY_Community 43|Community 43]]
- [[_COMMUNITY_Community 44|Community 44]]
- [[_COMMUNITY_Community 45|Community 45]]
- [[_COMMUNITY_Community 46|Community 46]]
- [[_COMMUNITY_Community 47|Community 47]]
- [[_COMMUNITY_Community 48|Community 48]]
- [[_COMMUNITY_Community 49|Community 49]]
- [[_COMMUNITY_Community 50|Community 50]]
- [[_COMMUNITY_Community 51|Community 51]]
- [[_COMMUNITY_Community 52|Community 52]]
- [[_COMMUNITY_Community 53|Community 53]]
- [[_COMMUNITY_Community 54|Community 54]]
- [[_COMMUNITY_Community 55|Community 55]]
- [[_COMMUNITY_Community 56|Community 56]]
- [[_COMMUNITY_Community 57|Community 57]]
- [[_COMMUNITY_Community 58|Community 58]]
- [[_COMMUNITY_Community 59|Community 59]]
- [[_COMMUNITY_Community 60|Community 60]]
- [[_COMMUNITY_Community 61|Community 61]]
- [[_COMMUNITY_Community 62|Community 62]]
- [[_COMMUNITY_Community 63|Community 63]]
- [[_COMMUNITY_Community 64|Community 64]]
- [[_COMMUNITY_Community 65|Community 65]]
- [[_COMMUNITY_Community 66|Community 66]]
- [[_COMMUNITY_Community 67|Community 67]]
- [[_COMMUNITY_Community 68|Community 68]]
- [[_COMMUNITY_Community 69|Community 69]]
- [[_COMMUNITY_Community 70|Community 70]]
- [[_COMMUNITY_Community 71|Community 71]]
- [[_COMMUNITY_Community 72|Community 72]]
- [[_COMMUNITY_Community 73|Community 73]]
- [[_COMMUNITY_Community 74|Community 74]]
- [[_COMMUNITY_Community 75|Community 75]]
- [[_COMMUNITY_Community 76|Community 76]]
- [[_COMMUNITY_Community 77|Community 77]]
- [[_COMMUNITY_Community 78|Community 78]]
- [[_COMMUNITY_Community 79|Community 79]]
- [[_COMMUNITY_Community 80|Community 80]]
- [[_COMMUNITY_Community 81|Community 81]]
- [[_COMMUNITY_Community 82|Community 82]]
- [[_COMMUNITY_Community 83|Community 83]]
- [[_COMMUNITY_Community 84|Community 84]]
- [[_COMMUNITY_Community 85|Community 85]]
- [[_COMMUNITY_Community 86|Community 86]]
- [[_COMMUNITY_Community 87|Community 87]]
- [[_COMMUNITY_Community 88|Community 88]]
- [[_COMMUNITY_Community 89|Community 89]]
- [[_COMMUNITY_Community 90|Community 90]]
- [[_COMMUNITY_Community 91|Community 91]]
- [[_COMMUNITY_Community 92|Community 92]]
- [[_COMMUNITY_Community 93|Community 93]]

## God Nodes (most connected - your core abstractions)
1. `QueryManager` - 52 edges
2. `MetadataManager` - 36 edges
3. `QueryExecutionError` - 28 edges
4. `Rule` - 26 edges
5. `GoogleBigQueryConnector` - 21 edges
6. `ConnectionError` - 20 edges
7. `ReportBuilder` - 20 edges
8. `Graphify Skill` - 20 edges
9. `DatabricksConnector` - 19 edges
10. `SnowflakeConnector` - 19 edges

## Surprising Connections (you probably didn't know these)
- `DataFrame` --uses--> `ValidationError`  [INFERRED]
  test/validate/test_schema.py → src/AnalystStack/exceptions/errors.py
- `DataReader` --uses--> `DataReader`  [INFERRED]
  test/io/test_io_reader.py → src/AnalystStack/io/reader.py
- `DataWriter` --uses--> `DataWriter`  [INFERRED]
  test/io/test_io_writer.py → src/AnalystStack/io/writer.py
- `AnalystStack (docs home)` --semantically_similar_to--> `AnalystStack`  [INFERRED] [semantically similar]
  docs/docs/index.md → README.md
- `IO` --semantically_similar_to--> `io facade`  [INFERRED] [semantically similar]
  README.md → docs/docs/io.md

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Connector Error Hierarchy** — connectors_datapackageerror, connectors_configurationerror, connectors_connectionerror, connectors_queryexecutionerror, connectors_validationerror [EXTRACTED 0.95]
- **AnalystStack Core Modules** — readme_connectors, readme_io, readme_formatting [EXTRACTED 0.85]
- **CI Quality Gates** — workflows_ci, workflows_tox, workflows_pypipublish [EXTRACTED 0.85]
- **Graphify Build Pipeline (detect → extract → cluster → output)** — skill_graphify_detect, skill_graphify_ast_extraction, skill_graphify_semantic_extraction, skill_graphify_clustering, skill_graphify_graph_json [EXTRACTED 1.00]
- **Graphify Graph Outputs** — skill_graphify_html_viz, skill_graphify_graph_report, skill_graphify_graph_json, skill_graphify_obsidian_vault [EXTRACTED 1.00]
- **Graphify Query/Path/Explain Interface** — references_query_bfs, references_query_dfs, references_query_path, references_query_explain, references_query_query_expansion [EXTRACTED 1.00]

## Communities (94 total, 26 thin omitted)

### Community 0 - "Graphify Skill & Exports"
Cohesion: 0.06
Nodes (50): Graphify Skill Trigger, Graphify Add URL, Watch Debounce, URL Ingest Pipeline, Folder Watcher (--watch), FalkorDB Export, MCP Stdio Server, Neo4j Export (+42 more)

### Community 1 - "BigQuery Manager Layer"
Cohesion: 0.10
Nodes (22): MetadataManager, Dedicated to schema extraction. Notice how we 'inject' the QueryManager so we do, Handles schema and structural metadata extraction from INFORMATION_SCHEMA., QueryManager, Dedicated to executing SQL and moving data, Handles read and write data operations to BigQuery.      `execute_read` runs thr, ProfilerManager, Dedicated to heavy analytical queries like calculating fill rates (+14 more)

### Community 2 - "Data IO Read/Write"
Cohesion: 0.07
Nodes (26): DataIOManager, Facade for all IO operations.      Bundles a `DataReader` and a `DataWriter` beh, DataReader, Reads a CSV file with advanced parsing options.          Thin wrapper around `pa, Reads Parquet files natively.          Args:             file_path: Path to the, Render a Jinja2 template and return the resulting string.          ``source`` ca, Handles comprehensive data ingestion into DataFrames.      Wraps `pandas.read_ex, Reads a specific range of an Excel sheet into a DataFrame.          ``start_cell (+18 more)

### Community 3 - "Connector Facade & Base Contract"
Cohesion: 0.19
Nodes (9): ABC, BaseConnector, Shared contract for every warehouse connector in this package.  Every connector, Abstract base class defining the contract every connector must implement.      C, Executes a query and returns a pandas DataFrame.          Args:             quer, Writes a DataFrame to a table in the destination system.          Args:, Lists every base table in a schema/dataset, with structural metadata.          A, Cloud data-warehouse connectors: read, write, and profile tables through a unifo (+1 more)

### Community 4 - "AnalystStack Docs & Roadmap"
Cohesion: 0.06
Nodes (39): BaseConnector Contract, ConfigurationError, ConnectionError, Databricks Connector, DataPackageError, GoogleBigQueryConnector (docs), QueryExecutionError, ValidationError (+31 more)

### Community 5 - "Settings & Error Handling"
Cohesion: 0.14
Nodes (9): DatabricksSettings, Uses standard dataclasses to pull from environment variables, avoiding hardcoded, Manages default settings for the Databricks environment., DatabricksConnector, Executes a SQL query against Databricks and returns the result as a DataFrame., Lists every base table in a Databricks schema, with structural metadata., Returns structural metadata for every column of a Databricks table.          Arg, Profiles every column of a Databricks table: structural metadata plus fill rate. (+1 more)

### Community 6 - "Format CLI"
Cohesion: 0.16
Nodes (20): _format_python(), _format_sql(), handle_format(), main(), The ``analyststack`` command-line entry point.  Installed as the console scrip, The main entry point for the CLI., Lint or format a Python file (operates on the file's contents as a string)., Lint or format a SQL file (SQLFluff operates directly on the file). (+12 more)

### Community 7 - "Code Formatters (Python/SQL)"
Cohesion: 0.08
Nodes (28): Enum, Formats and lints generated code so it comes out tidy and consistent.  Exposes t, PythonFormatter, Handles Python linting and formatting using Ruff and AST.      Wraps [Ruff's](ht, Initializes the formatter.          Args:             line_length: Maximum line, Checks for fundamental Python syntax errors without executing the code., Formats Python code using Ruff's formatter.          Runs ``code_string`` throug, FormattingLevel (+20 more)

### Community 8 - "Client Wrappers (Auth)"
Cohesion: 0.29
Nodes (6): Creates and validates the SQLAlchemy engine and native client for a BigQuery pro, The native ``google.cloud.bigquery.Client`` used for `load_table_from_dataframe`, Client, ConnectionError, Raised when authentication or client initialization fails., Raised when a SQL query or DataFrame write operation fails.

### Community 9 - "BigQuery Connector Tests"
Cohesion: 0.05
Nodes (25): GoogleBigQueryConnector, The Facade (The Final Connecter)  This is what your end-users will interact with, Lists every base table in a BigQuery dataset, with structural metadata., Returns structural metadata for every column of a BigQuery table.          Args:, Profiles every column of a BigQuery table: structural metadata plus fill rate., Facade combining BigQuery client, query, metadata, and profiling logic.      Rea, Executes a SQL query against BigQuery and returns the result as a DataFrame., Google BigQuery connector: `GoogleBigQueryConnector` and its supporting client/q (+17 more)

### Community 10 - "DataReader Tests"
Cohesion: 0.17
Nodes (3): DataReader, Tests for AnalystStack.io.reader.DataReader (jinja + csv)., reader()

### Community 11 - "DataWriter Tests"
Cohesion: 0.20
Nodes (3): DataWriter, Tests for AnalystStack.io.writer.DataWriter (csv, markdown, txt)., writer()

### Community 12 - "Python Formatter Tests"
Cohesion: 0.22
Nodes (3): formatter(), Tests for AnalystStack.format.python.PythonFormatter., PythonFormatter

### Community 13 - "Excel Cell Parsing"
Cohesion: 0.06
Nodes (39): PostgresSettings, Manages default settings for the Postgres environment., connector(), A pre-initialised connector wired to the mocked engine., Missing connection settings (args and env) raise ConfigurationError., A failure while creating/connecting the engine raises ConnectionError., test_initialization_missing_settings(), test_initialization_wraps_engine_errors() (+31 more)

### Community 14 - "Metadata Extraction"
Cohesion: 0.20
Nodes (7): MetadataManager, Dedicated to schema extraction. Notice how we 'inject' the QueryManager so we do, Handles schema and structural metadata extraction from INFORMATION_SCHEMA., Lists every base table in a Databricks schema, with structural metadata., Returns structural metadata for every column of a Databricks table.          Arg, DataFrame, QueryManager

### Community 15 - "Test Fixtures"
Cohesion: 0.40
Nodes (4): DataFrame, Shared pytest fixtures for the AnalystStack test suite., A small, well-formed DataFrame reused across IO and connector tests., sample_dataframe()

### Community 16 - "BigQuery Table ID Utils"
Cohesion: 0.50
Nodes (3): construct_full_table_id(), BigQuery-specific text parsing and helper functions., Builds a backtick-quoted ``project.dataset.table`` reference for BigQuery Standa

### Community 17 - "Logging"
Cohesion: 0.50
Nodes (3): Logger, get_logger(), Creates and returns a configured logger.

### Community 26 - "Community 26"
Cohesion: 0.11
Nodes (24): DataFrame, Rule, DataFrame, check_schema(), enforce_schema(), Whole-frame structural validation: column existence, ordering, and dtype checks., Checks `df` against `expected_columns` and raises if it doesn't match.      Mirr, Wraps :func:`check_schema` as a single pass/fail `Rule`, for `Validator` composi (+16 more)

### Community 27 - "Community 27"
Cohesion: 0.08
Nodes (23): For /graphify add and --watch, For /graphify query, For the commit hook and native CLAUDE.md integration, For --update and --cluster-only, /graphify, Honesty Rules, Interpreter guard for subcommands, Part A - Structural extraction for code files (+15 more)

### Community 28 - "Community 28"
Cohesion: 0.12
Nodes (19): compare_dataframes(), Key-by-key comparison of two DataFrames: schema drift, unmatched rows, and value, Compares two DataFrames that share a key, cell by cell.      Reports schema drif, One-call exploratory-data-analysis profile of a single DataFrame., Profiles every column of ``df`` in one call: dtype, null counts, cardinality, an, summarize(), left(), Tests for AnalystStack.compare. (+11 more)

### Community 29 - "Community 29"
Cohesion: 0.14
Nodes (12): DuckDBSettings, Manages default settings for the DuckDB environment., DuckDBConnector, The Facade (The Final Connector)  This is what your end-users will interact with, Returns structural metadata for every column of a DuckDB table.          Args:, Profiles every column of a DuckDB table: structural metadata plus fill rate., Facade combining DuckDB client, query, metadata, and profiling logic.      DuckD, Executes a SQL query against DuckDB and returns the result as a DataFrame. (+4 more)

### Community 30 - "Community 30"
Cohesion: 0.15
Nodes (17): CheckResult, DataFrame, Rule, DataFrame, check_referential_integrity(), Referential-integrity checks between two DataFrames.  Pairs naturally with :mod:, Checks that every value in `child`'s `child_column` exists in `parent`'s `parent, Wraps a referential-integrity check as a `Rule`, for `Validator` composition. (+9 more)

### Community 31 - "Community 31"
Cohesion: 0.15
Nodes (16): Rule, not_null(), Builds a rule that fails every row that shares its ``column`` value with another, Builds a rule that fails any row where ``column`` is null.      Args:         co, unique(), test_not_null_flags_missing_values(), test_unique_flags_all_duplicates(), test_validator_add_chains() (+8 more)

### Community 32 - "Community 32"
Cohesion: 0.13
Nodes (13): Writes a DataFrame to a BigQuery table.          Args:             df: The DataF, ProfilerManager, Dedicated to heavy analyticial queries like calculating fill rates, Generates data quality statistics and profiles.      Args:         query_manager, Profiles every column of a BigQuery table: structural metadata plus fill rate., Writes a DataFrame to a Databricks table.          Args:             df: The Dat, Writes a DataFrame to a Snowflake table.          Args:             df: The Data, DataFrame (+5 more)

### Community 33 - "Community 33"
Cohesion: 0.11
Nodes (7): connector(), mock_engine(), Tests for AnalystStack.connectors.DatabricksConnector.  ``sqlalchemy.create_engi, Patches ``create_engine`` used inside the client wrapper., A pre-initialised connector wired to the mocked engine., A failure while creating/connecting the engine raises ConnectionError., test_initialization_wraps_engine_errors()

### Community 34 - "Community 34"
Cohesion: 0.12
Nodes (6): connector(), Tests for AnalystStack.connectors.DuckDBConnector.  Unlike the other connector t, A fresh in-memory DuckDB connector, with an ``orders`` table pre-populated., test_default_database_path_is_in_memory(), test_list_tables_empty_schema_has_correct_columns(), DuckDBConnector

### Community 35 - "Community 35"
Cohesion: 0.12
Nodes (12): Manages default settings for the Snowflake environment., SnowflakeSettings, Missing connection settings (args and env) raise ConfigurationError., A failure while creating/connecting the engine raises ConnectionError., test_initialization_missing_settings(), test_initialization_wraps_engine_errors(), Executes a SQL query against Snowflake and returns the result as a DataFrame., Lists every base table in a Snowflake schema, with structural metadata. (+4 more)

### Community 36 - "Community 36"
Cohesion: 0.18
Nodes (15): DataFrame, DataFrame, from_tidy(), Reshape DataFrames between tidy (long) and normal (wide) layouts.  The two shape, Reshapes a wide DataFrame into tidy (long) format: one row per observation., Reshapes a tidy (long) DataFrame back into normal (wide) format — the inverse of, to_tidy(), Tests for AnalystStack.tidy. (+7 more)

### Community 37 - "Community 37"
Cohesion: 0.18
Nodes (16): DataFrame, no_duplicate_rows(), no_outliers(), Builds a rule that fails every row if the frame's total row count is out of boun, Builds a rule that fails every row that's a duplicate of another, across ``subse, Builds a rule that fails any row where ``column`` is a statistical outlier., row_count_between(), df() (+8 more)

### Community 38 - "Community 38"
Cohesion: 0.15
Nodes (16): has_dtype(), in_range(), is_in(), matches_regex(), The ``Rule`` type and the factory functions that build the built-in rules.  Each, Builds a rule that fails any row where ``column`` falls outside ``[min_value, ma, Builds a rule that fails any row whose ``column`` value is not one of ``allowed`, Builds a rule that fails any row where ``column`` doesn't match ``pattern``. (+8 more)

### Community 39 - "Community 39"
Cohesion: 0.12
Nodes (5): connector(), mock_engine(), Tests for AnalystStack.connectors.SnowflakeConnector.  ``sqlalchemy.create_engin, Patches ``create_engine`` used inside the client wrapper., A pre-initialised connector wired to the mocked engine.

### Community 40 - "Community 40"
Cohesion: 0.15
Nodes (12): CheckResult, DataFrame, Series, CheckResult, Result types produced by evaluating validation :class:`~AnalystStack.validate.ru, The outcome of evaluating a single ``Rule`` against a DataFrame.      Returned b, Returns the subset of :attr:`results` that failed.          Returns:, custom() (+4 more)

### Community 41 - "Community 41"
Cohesion: 0.14
Nodes (3): mock_engine(), Tests for AnalystStack.connectors.PostgresConnector.  ``sqlalchemy.create_engine, Patches ``create_engine`` used inside the client wrapper.

### Community 42 - "Community 42"
Cohesion: 0.20
Nodes (11): `ReportBuilder`: a chainable builder for assembling a `DataQualityReport`., Chainable builder that assembles a `DataQualityReport` from other AnalystStack r, Initializes the builder.          Args:             title: The report's title., ReportBuilder, Tests for AnalystStack.report.builder.ReportBuilder., test_add_comparison_includes_match_rate_narrative(), test_add_dataframe_appends_a_section(), test_add_table_catalog_and_column_profile_naming() (+3 more)

### Community 43 - "Community 43"
Cohesion: 0.24
Nodes (8): QueryManager, Execute SQL in Databricks: Read and Write data, Handles read and write data operations to Databricks.      Every method runs thr, Runs a SQL query and returns the result as a DataFrame.          Args:, Writes a DataFrame to a catalog-qualified Databricks table.          Args:, DatabricksClientWrapper, QueryExecutionError, DataFrame

### Community 44 - "Community 44"
Cohesion: 0.20
Nodes (7): MetadataManager, Dedicated to schema extraction, via DuckDB's own catalog table functions rather, Handles schema and structural metadata extraction from DuckDB's catalog function, Lists every base table in a DuckDB schema, with structural metadata.          Us, Returns structural metadata for every column of a DuckDB table.          Uses ``, DataFrame, QueryManager

### Community 45 - "Community 45"
Cohesion: 0.20
Nodes (7): QueryManager, Execute SQL in DuckDB: Read and Write data, Handles read and write data operations to DuckDB.      Every method runs through, Runs a SQL query and returns the result as a DataFrame.          Args:, Writes a DataFrame to a schema-qualified DuckDB table.          Args:, DuckDBClientWrapper, DataFrame

### Community 46 - "Community 46"
Cohesion: 0.25
Nodes (8): DataPackageError, Raised when input validation fails (e.g., malformed table names)., Base exception for the package., ValidationError, DataFrame, ValidationReport, Evaluates every rule and returns a report — never raises.          Args:, Validates ``df`` and raises if any rule fails; returns ``df`` unchanged otherwis

### Community 47 - "Community 47"
Cohesion: 0.20
Nodes (7): MetadataManager, Dedicated to schema extraction. Notice how we 'inject' the QueryManager so we do, Handles schema and structural metadata extraction from INFORMATION_SCHEMA., Lists every base table in a Postgres schema, with structural metadata., Returns structural metadata for every column of a Postgres table.          Args:, DataFrame, QueryManager

### Community 48 - "Community 48"
Cohesion: 0.20
Nodes (7): QueryManager, Dedicated to executing postgres SQL and moving data, Handles read and write data operations to Postgres.      Every method runs thr, Runs a SQL query and returns the result as a DataFrame.          Args:, Writes a DataFrame to a schema-qualified Postgres table.          Args:, PostgresClientWrapper, DataFrame

### Community 49 - "Community 49"
Cohesion: 0.24
Nodes (6): One section of a `DataQualityReport`.      Attributes:         name: The section, ReportSection, Tests for AnalystStack.report.report., report(), test_write_excel_truncates_long_sheet_names(), DataQualityReport

### Community 50 - "Community 50"
Cohesion: 0.20
Nodes (7): MetadataManager, Dedicated to schema extraction. Notice how we 'inject' the QueryManager so we do, Handles schema and structural metadata extraction from INFORMATION_SCHEMA., Lists every base table in a Snowflake schema, with structural metadata., Returns structural metadata for every column of a Snowflake table.          Args, DataFrame, QueryManager

### Community 51 - "Community 51"
Cohesion: 0.20
Nodes (7): QueryManager, Execute SQL in Snowflake: Read and Write data, Handles read and write data operations to Snowflake.      Every method runs thro, Runs a SQL query and returns the result as a DataFrame.          Args:, Writes a DataFrame to a schema-qualified Snowflake table.          Args:, SnowflakeClientWrapper, DataFrame

### Community 52 - "Community 52"
Cohesion: 0.20
Nodes (7): Adds a `ValidationReport` as a section, rendered via `ValidationReport.to_frame`, ValidationReport, DataFrame, The combined outcome of every ``Rule`` a ``Validator`` evaluated.      Returned, ``True`` only if every rule in :attr:`results` passed., Renders the report as a DataFrame — one row per rule evaluated.          Returns, ValidationReport

### Community 53 - "Community 53"
Cohesion: 0.24
Nodes (6): DataQualityReport, The `DataQualityReport`/`ReportSection` result types and their file-writing logi, Writes one sheet per section that carries a DataFrame.          `io.write.excel`, A titled, ordered collection of `ReportSection`\\ s, ready to write to a file., Writes this report to a file, entirely through `AnalystStack.io.io.write`., Shared body for the markdown/txt formats, which differ only in which         `An

### Community 54 - "Community 54"
Cohesion: 0.22
Nodes (6): BigQueryClientWrapper, The Bigquery Engine (Composition Module)  Isolates authentication and API connec, Builds and wraps both connections BigQuery reads/writes need: a SQLAlchemy ``Eng, The underlying SQLAlchemy `Engine` used to run reads and metadata/profiling quer, BigQueryClientWrapper, Engine

### Community 55 - "Community 55"
Cohesion: 0.22
Nodes (6): Lists every base table in a BigQuery dataset, with structural metadata., Returns structural metadata for every column of a BigQuery table.          Args:, DataFrame, Ensures safety before executing costly cloud operations, Validates that a single identifier conforms to standard SQL naming rules.      A, validate_identifier()

### Community 56 - "Community 56"
Cohesion: 0.22
Nodes (6): DatabricksClientWrapper, The Databricks Engine (Composition Module)  Isolates authentication and API conn, Builds and wraps a SQLAlchemy ``Engine`` for Databricks via the     ``databricks, Creates and validates the SQLAlchemy engine for a Databricks SQL warehouse., The underlying SQLAlchemy `Engine` used to run reads and writes., Engine

### Community 57 - "Community 57"
Cohesion: 0.22
Nodes (6): DuckDBClientWrapper, The DuckDB Engine (Composition Module)  Isolates authentication and API connecti, Builds and wraps a SQLAlchemy ``Engine`` for DuckDB via the ``duckdb-engine`` di, Creates and validates the SQLAlchemy engine for a DuckDB database.          Args, The underlying SQLAlchemy `Engine` used to run reads and writes., Engine

### Community 58 - "Community 58"
Cohesion: 0.22
Nodes (6): PostgresClientWrapper, The Postgres Engine (Composition Module)  Isolates authentication and API conn, Builds and wraps a SQLAlchemy ``Engine`` for Postgres via the ``psycopg2`` drive, Creates and validates the SQLAlchemy engine for a Postgres database., The underlying SQLAlchemy `Engine` used to run reads and writes., Engine

### Community 59 - "Community 59"
Cohesion: 0.22
Nodes (8): graphify reference: extra exports and benchmark, Step 6b - Wiki (only if --wiki flag), Step 7 - Neo4j export (only if --neo4j or --neo4j-push flag), Step 7a - FalkorDB export (only if --falkordb or --falkordb-push flag), Step 7b - SVG export (only if --svg flag), Step 7c - GraphML export (only if --graphml flag), Step 7d - MCP server (only if --mcp flag), Step 8 - Token reduction benchmark (only if total_words > 5000)

### Community 60 - "Community 60"
Cohesion: 0.31
Nodes (5): Adds a connector's ``list_tables`` output as a section.          Args:, Adds a connector's ``profile_columns`` output as a section.          Args:, Adds an arbitrary DataFrame as a section.          The escape hatch for anything, Adds a `AnalystStack.compare.summarize` output as a section.          Args:, DataFrame

### Community 61 - "Community 61"
Cohesion: 0.22
Nodes (6): The Snowflake Engine (Composition Module)  Isolates authentication and API conne, Builds and wraps a SQLAlchemy ``Engine`` for Snowflake via the     ``snowflake-s, Creates and validates the SQLAlchemy engine for a Snowflake account.          Ar, The underlying SQLAlchemy `Engine` used to run reads and writes., SnowflakeClientWrapper, Engine

### Community 62 - "Community 62"
Cohesion: 0.22
Nodes (6): ValidationReport, pandera_errors_to_report(), Optional bridge from pandera's failure output into this package's `ValidationRep, Converts a pandera `SchemaErrors` exception into a `ValidationReport`.      Args, Tests for AnalystStack.validate.pandera_bridge.  Requires the optional ``pandera, test_pandera_errors_to_report_groups_failures_by_column_and_check()

### Community 63 - "Community 63"
Cohesion: 0.25
Nodes (8): test_read_data_failure(), test_write_data_wraps_load_job_errors(), test_read_data_failure(), test_read_data_failure(), test_write_data_wraps_failures(), test_read_data_failure(), test_write_data_wraps_failures(), Exception

### Community 64 - "Community 64"
Cohesion: 0.29
Nodes (5): ComparisonResult, The outcome of comparing two DataFrames on a shared key.      Returned by :func:, True if both DataFrames have identical columns, keys, and values., ComparisonResult, Adds a `ComparisonResult` as a section: match rates plus the value-differences t

### Community 65 - "Community 65"
Cohesion: 0.29
Nodes (6): :material-book-open-variant: Docs & DX, :material-chart-box: Analyst features, :material-check-all: Recently done (v0.2.0 — data quality & observability), :material-package-variant: Packaging & dependencies, :material-test-tube: Testing & quality, Roadmap / Next steps

### Community 66 - "Community 66"
Cohesion: 0.29
Nodes (5): ProfilerManager, Dedicated to heavy analytical queries like calculating fill rates, Generates data quality statistics and profiles.      Args:         query_manager, Profiles every column of a DuckDB table: structural metadata plus fill rate., DataFrame

### Community 67 - "Community 67"
Cohesion: 0.29
Nodes (5): ProfileManager, Dedicated to heavy analytical queries like calculating fill rates, Generates data quality statistics and profiles.      Args:         query_manager, Profiles every column of a Postgres table: structural metadata plus fill rate., DataFrame

### Community 68 - "Community 68"
Cohesion: 0.29
Nodes (5): ProfilerManager, Dedicated to heavy analytical queries like calculating fill rates, Generates data quality statistics and profiles.      Args:         query_manager, Profiles every column of a Snowflake table: structural metadata plus fill rate., DataFrame

### Community 69 - "Community 69"
Cohesion: 0.33
Nodes (5): For /graphify explain, For /graphify path, graphify reference: query, path, explain, Step 0 — Constrained query expansion (REQUIRED before traversal), Step 1 — Traversal

### Community 70 - "Community 70"
Cohesion: 0.40
Nodes (3): Runs a SQL query and returns the result as a DataFrame.          Args:, Bulk-loads a DataFrame into a fully-qualified BigQuery table via a load job., DataFrame

### Community 71 - "Community 71"
Cohesion: 0.40
Nodes (4): AnalystStack, Installation, Quickstart, What's inside

### Community 72 - "Community 72"
Cohesion: 0.40
Nodes (5): Timedelta, Timestamp, is_fresh(), Builds a rule that fails any row where ``column`` is older than ``max_age``., test_is_fresh_flags_stale_and_null_values()

### Community 73 - "Community 73"
Cohesion: 0.50
Nodes (3): For /graphify add, For --watch, graphify reference: add a URL and watch a folder

### Community 74 - "Community 74"
Cohesion: 0.50
Nodes (3): For git commit hook, For native CLAUDE.md integration, graphify reference: commit hook and native CLAUDE.md integration

### Community 75 - "Community 75"
Cohesion: 0.50
Nodes (3): For --cluster-only, For --update (incremental re-extraction), graphify reference: incremental update and cluster-only

## Knowledge Gaps
- **104 isolated node(s):** `Namespace`, `DataFrame`, `DataFrame`, `Any`, `Logger` (+99 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **26 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `ValidationError` connect `Community 46` to `Community 32`, `Community 34`, `Community 37`, `Community 55`, `Community 26`, `Community 31`?**
  _High betweenness centrality (0.244) - this node is a cross-community bridge._
- **Why does `ValidationReport` connect `Community 52` to `Community 64`, `Community 40`, `Community 42`, `Community 46`, `Community 79`, `Community 60`, `Community 62`, `Community 31`?**
  _High betweenness centrality (0.115) - this node is a cross-community bridge._
- **Why does `DataPackageError` connect `Community 46` to `Client Wrappers (Auth)`, `Community 43`, `Excel Cell Parsing`, `Community 63`?**
  _High betweenness centrality (0.099) - this node is a cross-community bridge._
- **Are the 47 inferred relationships involving `QueryManager` (e.g. with `GoogleBigQueryConnector` and `MetadataManager`) actually correct?**
  _`QueryManager` has 47 INFERRED edges - model-reasoned connections that need verification._
- **Are the 31 inferred relationships involving `MetadataManager` (e.g. with `GoogleBigQueryConnector` and `QueryManager`) actually correct?**
  _`MetadataManager` has 31 INFERRED edges - model-reasoned connections that need verification._
- **Are the 25 inferred relationships involving `QueryExecutionError` (e.g. with `QueryManager` and `.execute_read()`) actually correct?**
  _`QueryExecutionError` has 25 INFERRED edges - model-reasoned connections that need verification._
- **Are the 11 inferred relationships involving `Rule` (e.g. with `CheckResult` and `DataFrame`) actually correct?**
  _`Rule` has 11 INFERRED edges - model-reasoned connections that need verification._