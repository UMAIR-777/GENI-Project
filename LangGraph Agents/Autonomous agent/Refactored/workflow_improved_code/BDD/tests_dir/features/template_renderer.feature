Feature: TemplateRenderer Template Rendering and Management  
  As a [User: Developer] I want to reliably load, render, cache, and validate Jinja2 prompt templates  
  so that my downstream systems always receive correct, nonempty, and up‑to‑date prompt strings without critical failures.

  Background:
    Given the [Component: TemplateRenderer] is initialized with [Directory: prompts_dir] present  

  # 1. Happy Path: simple render
  Scenario: [UserAction: RenderSimpleTemplate] successfully renders a basic prompt  
    Given the [File: prompts/welcome.jinja2] exists  
    When I call the [Function: render_prompt] on [Component: TemplateRenderer]  
      with template_path = "welcome.jinja2"  
      and context = {"username": "Alice"}  
    Then the [Output: rendered_string] contains "Welcome, Alice!"  

  # 2. Missing prompts directory
  Scenario: [ErrorCondition: MissingPromptsDirectory] initialization fails  
    Given the [Directory: prompts_dir] does not exist  
    When I instantiate the [Class: TemplateRenderer]  
    Then a [Exception: RuntimeError] is raised  
    And the error message matches /Prompts directory not found/  

  # 3. Template not found
  Scenario: [ErrorCondition: TemplateNotFound] raises specific exception  
    Given no file named [File: prompts/unknown.jinja2] exists  
    When I call the [Function: render_prompt] with template_path = "unknown.jinja2"  
    Then a [Exception: TemplateNotFound] is raised  

  # 4. Empty template file
  Scenario: [ErrorCondition: EmptyRenderOutput] raises RuntimeError  
    Given the [File: prompts/blank.jinja2] contains only whitespace  
    When I call the [Function: render_prompt] with template_path = "blank.jinja2"  
    Then a [Exception: RuntimeError] is raised  
    And the error message matches /Rendered prompt is empty/  

  # 5. Context serialization: dict
  Scenario: [UserAction: RenderWithDictContext] serializes dict properly  
    Given the [File: prompts/data.jinja2] expects JSON for {{config}}  
    When I call the [Function: render_prompt] with  
      template_path = "data.jinja2"
      and context = {"config": {"x":10, "y":20}}  
    Then the [Output: rendered_string] contains a JSON block with keys "x" and "y"  

  # 6. Context serialization: object
  Scenario: [UserAction: RenderWithObjectContext] serializes object via __dict__  
    Given the [Class: Dummy] instance dummy with attributes a=1, b=2  
    And the [File: prompts/data.jinja2] expects JSON for {{obj}}  
    When I call the [Function: render_prompt] with  
      template_path = "data.jinja2"  
      and context = {"obj": dummy}  
    Then the [Output: rendered_string] contains fields "a": 1 and "b": 2  

  # 7. Mixed context types
  Scenario: [UserAction: RenderWithMixedContext] handles dict, list, object  
    Given the [File: prompts/mixed.jinja2] expects {{items}} and {{obj}}  
    And context = {"items": [1,2,3], "obj": dummy}  
    When I call the [Function: render_prompt]  
    Then the [Output: rendered_string] contains "[\n  1,\n  2,\n  3\n]"  
    And contains object fields "a": 1  

  # 8. Extension normalization
  Scenario: [RuleTest: TemplateNameValidation] enforces .jinja2 extension  
    Given template_name = "example.txt"  
    When I call the [Function: get_template_path] with template_name  
    Then the returned template_name matches /.*\.jinja2$/  

  # 9. Cache hit avoids reload
  Scenario: [PerformanceTest: CacheHit] uses cache on repeated render  
    Given the [Component: TemplateRenderer::_cache] is empty  
    And the [File: prompts/cache_test.jinja2] exists  
    When I call [Function: render_prompt] twice with same template_path and context  
    Then the second call does not access the file system  
    And the [Metric: cache_hit] increments  

  # 10. Cache invalidation manual
  Scenario: [UserAction: ManualCacheClear] reloads after cache clear  
    Given a template is loaded into [Component: TemplateRenderer::_cache]  
    When I clear the [Component: TemplateRenderer::_cache]  
    And I call [Function: render_prompt] again  
    Then the template is reloaded from disk  

  # 11. Cache invalidation on file change
  Scenario: [ModelTest: FileWatcherIntegration] invalidates cache on change  
    Given a file watcher monitors [File: prompts/alert.jinja2]  
    When the file watcher sends a modification event  
    Then the [Component: TemplateRenderer::_cache] entry for "alert.jinja2" is removed  

  # 12. Large template performance
  Scenario: [PerformanceTest: LargeTemplate] renders under threshold  
    Given the [File: prompts/large.jinja2] size > 1MB  
    When I measure the time to call [Function: render_prompt]  
    Then the [Metric: render_time] is less than 500ms  

  # 13. Thread-safety under concurrency
  Scenario: [ConcurrencyTest: ParallelRender] no race conditions  
    Given multiple threads call [Function: render_prompt] on "welcome.jinja2" concurrently  
    When all threads complete  
    Then each [Output: rendered_string] equals the single-threaded result  

  # 14. Unsupported context type
  Scenario: [ChaosTest: UnsupportedContextType] raises clear error  
    Given context = {"bad": object()}  
    When I call [Function: render_prompt] with template_path = "welcome.jinja2"  
    Then a [Exception: RuntimeError] is raised  
    And the error message mentions unsupported type  

  # 15. JSON indent impact
  Scenario: [EdgeCase: JSONIndentFormatting] respects indentation config  
    Given the [Component: TemplateRenderer] is configured with indent=None  
    When I render a dict context  
    Then the [Output: rendered_string] contains compact JSON  

  # 16. Logging on load and render
  Scenario: [UserAction: Logging] logs at INFO and DEBUG levels  
    Given the logger level is set to DEBUG  
    When I call [Function: render_prompt]  
    Then a DEBUG log "Loaded template:" is emitted  
    And an INFO log "TemplateManager initialized" exists  

  # 17. Error masking prevention
  Scenario: [ErrorCondition: SpecificException] does not wrap TemplateNotFound  
    Given no file "missing.jinja2" exists  
    When I call [Function: render_prompt]  
    Then the exception type is TemplateNotFound  
    And not a generic RuntimeError  

  # 18. Integration: missing loader config
  Scenario: [IntegrationTest: LoaderMisconfig] fails with clear error  
    Given the [Environment: Jinja2] is initialized with wrong loader path  
    When I call [Function: render_prompt]  
    Then a [Exception: TemplateNotFound] is raised  
    And the error message indicates loader path issue  

  # 19. Model-based state transitions
  Scenario: [ModelTest: RenderStateMachine] transitions through states  
    Given the system model state = "initialized"  
    When I call [Function: render_prompt]  
    Then the state transitions to "loaded"  
    And then to "rendered"  

  # 20. Z3 rule: template name constraints
  Scenario: [RuleTest: NameCharValidation] disallows illegal chars  
    Given template_name = "bad\\name.jinja2"  
    When I call [Function: get_template_path]  
    Then a [Exception: RuntimeError] is raised  
    And the error message mentions invalid characters  

  # 31. Subdirectory path support
  Scenario: [RuleTest: SubdirectoryPath] allows forward slashes in paths
    Given template_name = "subdir/template.jinja2"
    When I call [Function: get_template_path]
    Then no exception is raised
    And the returned path contains "subdir/template.jinja2"

  # 21. Chaos: filesystem permission error
  Scenario: [ChaosTest: FSReadError] surfaces IO errors  
    Given the [File: prompts/protected.jinja2] has no read permissions  
    When I call [Function: render_prompt]  
    Then an [Exception: IOError] is raised  
    And the error message mentions permission denied  

  # 22. Edge: extremely deep context nesting
  Scenario: [EdgeCase: DeepContext] handles nested dict/list up to depth 10  
    Given context is a nested dict 10 levels deep  
    When I call [Function: render_prompt]  
    Then no stack overflow occurs  
    And the [Output: rendered_string] is correctly populated  

  # 23. Parameterized: various file extensions
  Scenario Outline: [PropertyTest: ExtensionVariations] accepts multiple input names  
    Given the [Component: TemplateRenderer] is initialized  
    When I call [Function: get_template_path] with template_name = "<input_name>"  
    Then the returned name is "<expected>"  

    Examples:
      | input_name          | expected             |
      | "test"              | "test.jinja2"        |
      | "hello.txt"         | "hello.jinja2"       |
      | "world.jinja2"      | "world.jinja2"       |

  # 24. Chaos: malformed template syntax
  Scenario: [ChaosTest: SyntaxErrorInTemplate] surfaces Jinja syntax errors  
    Given the [File: prompts/bad_syntax.jinja2] contains "{% if %}"  
    When I call [Function: render_prompt]  
    Then a [Exception: TemplateSyntaxError] is raised  

  # 25. Security: context injection attack
  Scenario: [SecurityTest: ContextInjection] escapes HTML in context  
    Given context = {"user_input": "<script>alert(1)</script>"}  
    And autoescape is enabled  
    When I call [Function: render_prompt] with template using {{ user_input }}  
    Then the [Output: rendered_string] contains "&lt;script&gt;alert(1)&lt;/script&gt;"  

  # 26. Integration: JSON output consumed by downstream API
  Scenario: [IntegrationTest: DownstreamAPI] rendered JSON is valid  
    Given the [File: prompts/json_output.jinja2] produces JSON  
    When I call [Function: render_prompt]  
    Then the [Output: rendered_string] is parseable by json.loads()  

  # 27. Edge: zero-byte template file
  Scenario: [EdgeCase: ZeroByteFile] treats as empty and errors  
    Given the [File: prompts/zero.jinja2] is zero bytes  
    When I call [Function: render_prompt]  
    Then a [Exception: RuntimeError] is raised  

  # 28. Performance: burst rendering under load
  Scenario: [PerformanceTest: BurstRender] handles 1000 renders in <5s  
    Given the [Component: TemplateRenderer] is initialized  
    When I perform 1000 consecutive calls to [Function: render_prompt]  
    Then total time is less than 5 seconds  

  # 29. Maintainability: configuration override
  Scenario: [UserAction: OverrideConfig] uses custom FileSystemLoader path  
    Given the [Component: TemplateRenderer] is constructed with custom prompts_dir  
    When I call [Function: render_prompt] on a template in the custom dir  
    Then the template is loaded from the custom path  

  # 30. State safety: exception does not corrupt cache
  Scenario: [ErrorCondition: FailedRender] leaves cache intact on error  
    Given a valid template is cached  
    And the template file is then replaced with bad syntax  
    When I call [Function: render_prompt]  
    Then the cache entry remains the previous valid template  
    And subsequent successful renders still work  
