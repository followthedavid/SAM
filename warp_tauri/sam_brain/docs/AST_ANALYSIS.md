# AST Analysis Report

**Generated:** 2026-01-29
**Files Analyzed:** 63
**Total Classes:** 323
**Total Top-Level Functions:** 353

---

## 1. Class Definitions with Methods

### `cognitive/app_knowledge_extractor.py`

**class `CommandParameter`** (line 42)
- *(no methods)*

**class `AppleScriptCommand`** (line 51)
- *(no methods)*

**class `ClassProperty`** (line 60)
- *(no methods)*

**class `ClassElement`** (line 69)
- *(no methods)*

**class `AppleScriptClass`** (line 76)
- *(no methods)*

**class `AppSuite`** (line 86)
- *(no methods)*

**class `ScriptingDictionary`** (line 95)
- *(no methods)*

**class `TableColumn`** (line 105)
- *(no methods)*

**class `TableSchema`** (line 114)
- *(no methods)*

**class `DatabaseSchema`** (line 122)
- *(no methods)*

**class `UIElement`** (line 130)
- *(no methods)*

**class `TrainingPair`** (line 138)
- *(no methods)*

**class `AppleScriptExtractor`** (line 149)
- `__init__(self, app_dirs)` (line 172)
- `get_scriptable_apps(self)` (line 183)
- `_has_apple_events(self, app)` (line 205)
- `extract_dictionary(self, app_name)` (line 232)
- `_parse_sdef(self, sdef_xml, app_name)` (line 275)
- `generate_training_pairs(self, app_dict)` (line 351)
- `to_dict(self, result)` (line 421)

**class `URLSchemeExtractor`** (line 524)
- `__init__(self, app_dirs)` (line 547)
- `extract_all_schemes(self)` (line 556)
- `extract_from_app(self, app_name)` (line 576)
- `_extract_from_app(self, app)` (line 593)
- `generate_training_pairs(self, schemes)` (line 625)

**class `AccessibilityExtractor`** (line 674)
- `__init__(self)` (line 693)
- `_check_accessibility(self)` (line 697)
- `extract_actions(self, app_name, max_depth)` (line 710)
- `_extract_element_actions(self, element, depth, max_depth)` (line 759)
- `find_all_actions(self, tree)` (line 814)
- `generate_training_pairs(self, app_name, elements)` (line 839)

**class `SQLiteExtractor`** (line 900)
- `__init__(self)` (line 931)
- `extract_schema(self, db_path)` (line 935)
- `extract_known_database(self, name)` (line 998)
- `generate_training_pairs(self, schema)` (line 1017)
- `to_dict(self, schema)` (line 1077)

### `cognitive/code_indexer.py`

**class `CodeEntity`** (line 25)
- *(no methods)*

**class `PythonParser`** (line 38)
- `parse(self, file_path, project_id)` (line 41)
- `_parse_function(self, node, file_path, lines, project_id, async_)` (line 82)
- `_parse_class(self, node, file_path, lines, project_id)` (line 128)

**class `JavaScriptParser`** (line 162)
- `parse(self, file_path, project_id)` (line 183)
- `_find_jsdoc(self, content, pos)` (line 268)
- `_get_snippet(self, lines, start, count)` (line 282)

**class `RustParser`** (line 288)
- `parse(self, file_path, project_id)` (line 304)
- `_find_doc_comment(self, lines, line_num)` (line 365)
- `_get_snippet(self, lines, start, count)` (line 374)

**class `CodeIndexer`** (line 380)
- `__init__(self, db_path)` (line 402)
- `_init_db(self)` (line 408)
- `index_project(self, project_path, project_id, force)` (line 446)
- `search(self, query, project_id, entity_type, limit)` (line 517)
- `get_stats(self, project_id)` (line 573)
- `clear_project(self, project_id)` (line 612)

### `cognitive/code_pattern_miner.py`

**class `PatternType`** (line 75)
- *(no methods)*

**class `CommitInfo`** (line 94)
- *(no methods)*

**class `FileDiff`** (line 118)
- *(no methods)*

**class `CodePattern`** (line 140)
- `to_training_example(self)` (line 183)

**class `CommitAnalyzer`** (line 208)
- `__init__(self)` (line 257)
- `classify_commit(self, message, files)` (line 264)
- `calculate_quality_score(self, commit, diff, pattern_type)` (line 308)
- `generate_instruction(self, pattern_type, language, commit_message)` (line 369)

**class `QualityFilter`** (line 417)
- `__init__(self)` (line 451)
- `should_skip_commit(self, commit)` (line 458)
- `should_skip_file(self, file_path)` (line 482)
- `should_skip_diff(self, diff)` (line 502)

**class `CodePatternMiner`** (line 533)
- `__init__(self, db_path)` (line 549)
- `_init_db(self)` (line 583)
- `_is_commit_processed(self, commit_hash, repo_path)` (line 646)
- `_mark_commit_processed(self, commit_hash, repo_path, patterns_count)` (line 663)
- `_store_pattern(self, pattern)` (line 686)
- `_get_commits(self, repo_path, limit, since)` (line 722)
- `_get_commit_files(self, repo_path, commit_hash)` (line 811)
- `_get_file_diff(self, repo_path, commit_hash, file_path)` (line 835)
- `_get_file_content_at_commit(self, repo_path, commit_hash, file_path, before)` (line 901)
- `mine_repository(self, repo_path, limit, since, incremental)` (line 936)
- `_log_mining_run(self, repo_path)` (line 1088)
- `mine_multiple_repos(self, repo_paths)` (line 1112)
- `export_training_data(self, output_path, min_quality, pattern_types, languages)` (line 1140)
- `get_stats(self)` (line 1207)
- `search_patterns(self, query, limit)` (line 1259)
- `get_pattern(self, pattern_id)` (line 1285)

### `cognitive/cognitive_control.py`

**class `ConfidenceLevel`** (line 27)
- *(no methods)*

**class `GoalStatus`** (line 36)
- *(no methods)*

**class `GoalPriority`** (line 45)
- *(no methods)*

**class `Confidence`** (line 55)
- `category(self)` (line 63)
- `to_dict(self)` (line 76)

**class `MetaCognition`** (line 86)
- `__init__(self, db_path)` (line 97)
- `_init_db(self)` (line 106)
- `estimate_confidence(self, query, context, response)` (line 136)
- `_assess_query_clarity(self, query)` (line 204)
- `_assess_context_relevance(self, query, context)` (line 233)
- `_assess_response_specificity(self, response)` (line 255)
- `_assess_domain_knowledge(self, query)` (line 277)
- `_get_past_performance(self, query)` (line 301)
- `record_outcome(self, query, confidence, success)` (line 312)
- `get_calibration_stats(self)` (line 329)

**class `Goal`** (line 363)
- `to_dict(self)` (line 376)

**class `GoalManager`** (line 391)
- `__init__(self, db_path)` (line 403)
- `_init_db(self)` (line 411)
- `create_goal(self, description, priority, parent_id, deadline)` (line 439)
- `_save_goal(self, goal)` (line 465)
- `get_goal(self, goal_id)` (line 491)
- `_row_to_goal(self, row)` (line 508)
- `activate_goal(self, goal_id)` (line 522)
- `update_progress(self, goal_id, progress)` (line 531)
- `_update_parent_progress(self, parent_id)` (line 544)
- `get_active_goals(self)` (line 561)
- `get_next_goal(self)` (line 573)
- `detect_conflicts(self)` (line 578)

**class `ReasoningStep`** (line 599)
- *(no methods)*

**class `ReasoningEngine`** (line 608)
- `__init__(self, llm_generator)` (line 618)
- `chain_of_thought(self, problem, context)` (line 621)
- `verify_reasoning(self, steps)` (line 674)

**class `AttentionController`** (line 700)
- `__init__(self, focus_duration)` (line 711)
- `score_salience(self, items, current_goal)` (line 718)
- `set_focus(self, item)` (line 759)
- `should_shift_attention(self, new_items)` (line 766)
- `get_attention_state(self)` (line 794)

**class `CognitiveControl`** (line 806)
- `__init__(self, db_path)` (line 811)
- `process_query(self, query, context)` (line 817)

### `cognitive/compression.py`

**class `TokenType`** (line 21)
- *(no methods)*

**class `ScoredToken`** (line 35)
- *(no methods)*

**class `TokenImportanceScorer`** (line 44)
- `__init__(self)` (line 74)
- `classify_token(self, token)` (line 77)
- `score_tokens(self, text, preserve_questions, preserve_entities)` (line 110)
- `_tokenize(self, text)` (line 185)
- `_get_idf(self, token)` (line 191)

**class `PromptCompressor`** (line 210)
- `__init__(self, target_ratio)` (line 241)
- `compress(self, text, target_tokens, preserve_structure)` (line 249)
- `_apply_phrase_replacements(self, text)` (line 305)
- `_compress_preserve_structure(self, tokens, target)` (line 317)
- `_compress_aggressive(self, tokens, target)` (line 341)
- `_clean_whitespace(self, text)` (line 353)
- `compress_conversation(self, messages, target_tokens)` (line 364)
- `get_compression_stats(self, original, compressed)` (line 404)

**class `QueryType`** (line 418)
- *(no methods)*

**class `CompressionStats`** (line 429)
- *(no methods)*

**class `ContextualCompressor`** (line 439)
- `__init__(self)` (line 478)
- `detect_query_type(self, query)` (line 483)
- `get_token_allocation(self, query, total_tokens)` (line 507)
- `compress_for_query(self, context, query, target_tokens)` (line 521)
- `get_last_stats(self)` (line 610)

### `cognitive/doc_indexer.py`

**class `DocEntity`** (line 29)
- *(no methods)*

**class `MarkdownParser`** (line 41)
- `parse(self, file_path, project_id)` (line 52)
- `_chunk_section(self, content, heading)` (line 118)

**class `CommentParser`** (line 156)
- `parse(self, file_path, project_id)` (line 194)
- `_parse_python(self, file_path, content, project_id)` (line 213)
- `_parse_javascript(self, file_path, content, project_id)` (line 253)
- `_parse_rust(self, file_path, content, project_id)` (line 292)
- `_collect_comment_blocks(self, content, pattern)` (line 354)
- `_clean_jsdoc(self, content)` (line 382)
- `_should_skip(self, content)` (line 392)

**class `DocIndexer`** (line 401)
- `__init__(self, db_path)` (line 418)
- `_init_db(self)` (line 425)
- `_get_embedding(self, text)` (line 471)
- `index_docs(self, path, project_id, force, with_embeddings)` (line 497)
- `search_docs(self, query, limit, doc_type, project_id, use_semantic)` (line 597)
- `_semantic_search(self, cur, query_embedding, limit, doc_type, project_id)` (line 632)
- `_keyword_search(self, cur, query, limit, doc_type, project_id)` (line 679)
- `get_doc_context(self, file_path)` (line 723)
- `get_stats(self, project_id)` (line 758)
- `clear_project(self, project_id)` (line 803)

### `cognitive/emotional_model.py`

**class `MoodState`** (line 25)
- `valence(self)` (line 37)
- `arousal(self)` (line 52)

**class `EmotionalState`** (line 68)
- `to_dict(self)` (line 75)

**class `EmotionalTrigger`** (line 87)
- `detect_triggers(cls, text)` (line 138)

**class `MoodStateMachine`** (line 163)
- `__init__(self)` (line 200)
- `update(self, triggers)` (line 208)
- `_apply_decay(self)` (line 255)
- `_record_transition(self, new_state)` (line 270)
- `get_mood_summary(self)` (line 276)

**class `ExpressionModulator`** (line 297)
- `modulate(self, response, state)` (line 344)

**class `UserModel`** (line 384)
- `to_dict(self)` (line 396)

**class `RelationshipTracker`** (line 408)
- `__init__(self, db_path)` (line 419)
- `_init_db(self)` (line 426)
- `get_or_create_user(self, user_id)` (line 459)
- `_save_user(self, user)` (line 489)
- `record_interaction(self, user_id, interaction_type, sentiment, topics)` (line 514)
- `add_inside_joke(self, user_id, joke)` (line 544)
- `get_relationship_context(self, user_id)` (line 552)

**class `EmotionalModel`** (line 579)
- `__init__(self, db_path)` (line 590)
- `process_input(self, text, user_id)` (line 595)
- `modulate_response(self, response)` (line 623)
- `get_emotional_context(self, user_id)` (line 627)
- `get_state(self)` (line 641)

### `cognitive/enhanced_learning.py`

**class `LearningOpportunity`** (line 30)
- *(no methods)*

**class `ActiveLearner`** (line 41)
- `__init__(self, db_path)` (line 52)
- `_init_db(self)` (line 61)
- `identify_uncertainty(self, query, response, confidence)` (line 96)
- `_classify_uncertainty(self, query, response, confidence)` (line 132)
- `_generate_learning_question(self, query, uncertainty_type)` (line 152)
- `_save_opportunity(self, opp)` (line 184)
- `get_top_learning_needs(self, n)` (line 201)
- `mark_learned(self, opportunity_id, topic, source)` (line 228)

**class `CacheEntry`** (line 255)
- *(no methods)*

**class `PredictiveCache`** (line 265)
- `__init__(self, db_path)` (line 278)
- `_init_db(self)` (line 287)
- `record_access(self, key, related_keys)` (line 314)
- `predict_needed(self, current_context, current_hour, n)` (line 348)
- `pre_warm(self, keys, content_getter)` (line 403)
- `get(self, key)` (line 428)
- `_evict_if_needed(self)` (line 435)

**class `SleepConsolidator`** (line 452)
- `__init__(self, memory_db_path)` (line 464)
- `start_background(self)` (line 471)
- `stop(self)` (line 480)
- `_consolidation_loop(self)` (line 486)
- `_should_consolidate(self)` (line 496)
- `consolidate(self)` (line 502)
- `_consolidate_db(self, db_path)` (line 535)
- `_log_consolidation(self, stats)` (line 589)

**class `EnhancedLearningSystem`** (line 596)
- `__init__(self, db_path)` (line 606)
- `process_interaction(self, query, response, confidence, context_keys)` (line 614)
- `get_learning_suggestions(self, n)` (line 633)
- `predict_context(self, current_context)` (line 638)
- `get_cached(self, key)` (line 642)
- `run_maintenance(self)` (line 646)
- `stop(self)` (line 650)

### `cognitive/enhanced_memory.py`

**class `MemoryType`** (line 29)
- *(no methods)*

**class `MemoryItem`** (line 40)
- `__post_init__(self)` (line 53)
- `to_dict(self)` (line 61)
- `from_dict(cls, data)` (line 76)

**class `WorkingMemory`** (line 80)
- `__init__(self, capacity)` (line 97)
- `add(self, content, memory_type, importance, metadata)` (line 103)
- `access(self, item_id)` (line 143)
- `focus(self, item_id)` (line 154)
- `decay(self)` (line 164)
- `get_active_items(self, threshold)` (line 173)
- `get_context_string(self, max_tokens)` (line 179)
- `clear(self)` (line 195)
- `_generate_id(self, content)` (line 201)

**class `Skill`** (line 208)
- `success_rate(self)` (line 221)
- `confidence(self)` (line 226)

**class `ProceduralMemory`** (line 234)
- `__init__(self, db_path)` (line 242)
- `_init_db(self)` (line 248)
- `add_skill(self, name, description, trigger_patterns, implementation, metadata)` (line 289)
- `find_matching_skills(self, input_text)` (line 325)
- `record_usage(self, skill_id, input_text, output_text, success, duration_ms)` (line 349)
- `get_skill(self, skill_id)` (line 383)
- `get_top_skills(self, n)` (line 400)
- `_row_to_skill(self, row)` (line 415)

**class `MemoryDecayManager`** (line 430)
- `__init__(self, db_path)` (line 444)
- `_init_db(self)` (line 449)
- `track_memory(self, memory_id, source_system, importance)` (line 474)
- `access_memory(self, memory_id)` (line 489)
- `get_weak_memories(self, threshold, source_system)` (line 533)
- `prune_memories(self, threshold)` (line 570)

**class `EnhancedMemoryManager`** (line 592)
- `__init__(self, working_memory_capacity, memory_db_path)` (line 603)
- `process_turn(self, user_input, response)` (line 615)
- `get_context(self, max_tokens)` (line 642)
- `add_fact(self, fact, importance)` (line 646)
- `add_skill(self, name, description, triggers, implementation)` (line 654)
- `find_skill(self, query)` (line 664)
- `run_maintenance(self)` (line 669)
- `get_stats(self)` (line 682)

### `cognitive/enhanced_retrieval.py`

**class `RetrievedChunk`** (line 68)
- `__hash__(self)` (line 76)
- `__eq__(self, other)` (line 79)

**class `EmbeddingModel`** (line 83)
- `__init__(self, model_name)` (line 89)
- `_init_model(self)` (line 94)
- `embed(self, texts)` (line 107)
- `_embed_ollama(self, texts)` (line 116)
- `embed_single(self, text)` (line 137)

**class `HyDERetriever`** (line 142)
- `__init__(self, embedding_model, llm_generator)` (line 155)
- `_default_generator(self, query)` (line 161)
- `generate_hypothetical(self, query)` (line 175)
- `get_hyde_embedding(self, query)` (line 179)
- `retrieve(self, query, documents, top_k)` (line 197)
- `_keyword_fallback(self, query, documents, top_k)` (line 233)

**class `EntityExtractor`** (line 249)
- `__init__(self)` (line 255)
- `extract(self, text)` (line 263)
- `_extract_spacy(self, text)` (line 269)
- `_extract_regex(self, text)` (line 284)

**class `MultiHopRetriever`** (line 318)
- `__init__(self, base_retriever, entity_extractor, max_hops)` (line 330)
- `retrieve(self, query, document_store, top_k_per_hop, top_k_final)` (line 337)

**class `CrossEncoderReranker`** (line 398)
- `__init__(self, model_name, use_lightweight)` (line 409)
- `_init_model(self)` (line 428)
- `_init_lightweight(self)` (line 439)
- `rerank(self, query, chunks, top_k)` (line 448)
- `_rerank_lightweight(self, query, chunks, top_k)` (line 476)
- `_rerank_crossencoder(self, query, chunks, top_k)` (line 509)

**class `QueryDecomposer`** (line 528)
- `decompose(self, query)` (line 539)

**class `DocumentStore`** (line 575)
- `__init__(self, db_paths, embedding_model)` (line 581)
- `search(self, query, top_k)` (line 587)
- `_search_db(self, db_path, query, top_k)` (line 599)

**class `EnhancedRetrievalSystem`** (line 660)
- `__init__(self, db_paths, use_hyde, use_multihop, use_reranking, use_code_index)` (line 674)
- `set_project(self, project_id)` (line 705)
- `_retrieve_from_code_index(self, query, limit)` (line 709)
- `retrieve(self, query, top_k, include_code)` (line 747)
- `retrieve_as_context(self, query, max_tokens)` (line 804)

### `cognitive/image_preprocessor.py`

**class `ImageFormat`** (line 66)
- *(no methods)*

**class `ImageInfo`** (line 78)
- `to_dict(self)` (line 90)

**class `PreprocessResult`** (line 106)
- `to_dict(self)` (line 119)

**class `ImagePreprocessor`** (line 139)
- `__init__(self, max_size, output_format, jpeg_quality, cache_dir)` (line 151)
- `pil_available(self)` (line 180)
- `get_image_info(self, path)` (line 191)
- `estimate_memory_needed(self, path, size, has_alpha)` (line 243)
- `preprocess_image(self, path, max_size, force_format, preserve_alpha)` (line 285)
- `preprocess_image_detailed(self, path, max_size, force_format, preserve_alpha)` (line 307)
- `_resize_image(self, img, max_size)` (line 461)
- `_detect_format(self, path, pil_format)` (line 478)
- `_needs_format_conversion(self, path, output_format, mode)` (line 512)
- `_get_cache_key(self, path, max_size, force_format, preserve_alpha)` (line 525)
- `_calc_memory_saved(self, original_size, processed_size)` (line 538)
- `cleanup_cache(self, max_age_hours)` (line 553)
- `clear_cache(self)` (line 582)

### `cognitive/learning_strategy.py`

**class `LearningTier`** (line 53)
- `name_readable(self)` (line 67)

**class `LearningPriority`** (line 80)
- `percentage_display(self)` (line 98)
- `__post_init__(self)` (line 102)

**class `ExampleAnalysis`** (line 109)
- *(no methods)*

**class `LearningStrategyFramework`** (line 118)
- `__init__(self, target_examples)` (line 177)
- `_build_priorities(self)` (line 188)
- `categorize_example(self, example)` (line 258)
- `score_example(self, example, tier)` (line 329)
- `_extract_content(self, example)` (line 369)
- `_assess_content_quality(self, content)` (line 378)
- `_calculate_coverage_gap(self, tier)` (line 415)
- `suggest_next_priority(self, current_coverage)` (line 434)
- `update_coverage(self, tier, count)` (line 471)
- `get_coverage_report(self)` (line 475)
- `get_tier_hierarchy(self)` (line 505)
- `apply_active_learning_filter(self, examples, known_examples)` (line 525)

### `cognitive/mlx_cognitive.py`

**class `ModelSize`** (line 44)
- *(no methods)*

**class `ModelConfig`** (line 51)
- *(no methods)*

**class `GenerationConfig`** (line 64)
- *(no methods)*

**class `GenerationResult`** (line 75)
- *(no methods)*

**class `MLXCognitiveEngine`** (line 130)
- `__init__(self, db_path)` (line 142)
- `generate(self, prompt, context, cognitive_state, config)` (line 161)
- `generate_streaming(self, prompt, context, cognitive_state, config)` (line 287)
- `_select_model(self, prompt, context, cognitive_state)` (line 398)
- `_load_model(self, model_key)` (line 460)
- `_format_prompt(self, prompt, context, cognitive_state, tokenizer, model_config)` (line 485)
- `_clean_response(self, response)` (line 529)
- `_truncate_repetition(self, text, min_repeat_length, max_repeats)` (line 548)
- `_detect_repetition_live(self, buffer)` (line 585)
- `_calculate_confidence(self, response, cognitive_state, repetition_detected)` (line 598)
- `_is_factual_response(self, response)` (line 668)
- `_should_escalate(self, response, confidence, repetition_detected)` (line 698)
- `_get_memory_pressure(self)` (line 725)
- `_estimate_complexity(self, query)` (line 734)
- `_fallback_response(self, prompt, error)` (line 771)
- `get_stats(self)` (line 784)
- `get_resource_snapshot(self)` (line 796)
- `unload_model(self)` (line 800)
- `get_memory_usage_mb(self)` (line 815)

### `cognitive/mlx_optimized.py`

**class `OptimizationConfig`** (line 35)
- *(no methods)*

**class `OptimizedMLXEngine`** (line 56)
- `__init__(self, db_path, optimization_config)` (line 67)
- `generate(self, prompt, context, cognitive_state, config, reuse_cache)` (line 87)
- `_generate_optimized(self, model, tokenizer, prompt, config, model_key, reuse_cache)` (line 195)
- `generate_streaming_optimized(self, prompt, context, cognitive_state, config)` (line 267)
- `clear_conversation_cache(self)` (line 374)
- `get_optimization_stats(self)` (line 379)

### `cognitive/model_evaluation.py`

**class `BenchmarkSuite`** (line 80)
- *(no methods)*

**class `MetricType`** (line 97)
- *(no methods)*

**class `TestStatus`** (line 131)
- *(no methods)*

**class `ModelGenerator`** (line 190)
- `__call__(self, prompt)` (line 193)

**class `EvaluationSample`** (line 204)
- *(no methods)*

**class `SampleResult`** (line 226)
- *(no methods)*

**class `EvaluationResults`** (line 252)
- `to_dict(self)` (line 292)
- `summary(self)` (line 317)

**class `ABTestConfig`** (line 350)
- *(no methods)*

**class `ABTestResults`** (line 385)
- `to_dict(self)` (line 419)
- `summary(self)` (line 442)

**class `HumanEvalBatch`** (line 478)
- `to_json(self)` (line 490)

**class `MetricCalculator`** (line 512)
- `calculate_bleu(reference, candidate, max_n)` (line 526)
- `_get_ngrams(tokens, n)` (line 574)
- `calculate_rouge_l(reference, candidate)` (line 579)
- `_lcs_length(a, b)` (line 615)
- `calculate_personality_consistency(response)` (line 638)
- `calculate_helpfulness(response, prompt)` (line 676)
- `calculate_safety_score(response)` (line 734)
- `calculate_code_correctness(response, expected)` (line 760)

**class `ModelEvaluator`** (line 954)
- `__init__(self, model_generator, output_dir, batch_size)` (line 1045)
- `_get_generator(self)` (line 1072)
- `evaluate(self, test_data, model_id, include_sample_results)` (line 1096)
- `_evaluate_sample(self, sample, generator)` (line 1194)
- `evaluate_benchmark(self, suite, model_id, custom_samples)` (line 1266)
- `evaluate_all_benchmarks(self, model_id)` (line 1291)
- `_save_results(self, results)` (line 1308)
- `get_stats(self)` (line 1316)

**class `ABTestFramework`** (line 1330)
- `__init__(self, output_dir, evaluator)` (line 1354)
- `create_test(self, model_a_generator, model_b_generator, model_a_id, model_b_id, name, description, metrics_to_compare, sample_size)` (line 1378)
- `run_test(self, test_id, test_data)` (line 1438)
- `_compare_results(self, test_results, results_a, results_b, test_data)` (line 1520)
- `_calculate_significance(self, wins_a, wins_b, ties, confidence_level)` (line 1602)
- `_normal_cdf(self, x)` (line 1661)
- `_select_example_comparisons(self, sample_a_by_id, sample_b_by_id, test_data, limit)` (line 1665)
- `get_winner(self, test_id)` (line 1705)
- `create_human_eval_batch(self, test_id, num_samples)` (line 1734)
- `process_human_eval_results(self, batch_id, results_file)` (line 1805)
- `_save_test_results(self, results)` (line 1850)
- `list_tests(self)` (line 1858)
- `get_test(self, test_id)` (line 1872)

### `cognitive/model_selector.py`

**class `TaskType`** (line 17)
- *(no methods)*

**class `SelectionResult`** (line 29)
- *(no methods)*

**class `DynamicModelSelector`** (line 37)
- `__init__(self)` (line 101)
- `select_model(self, query, context_tokens, confidence_required, memory_pressure, task_type)` (line 105)
- `_detect_task_type(self, query)` (line 217)
- `_estimate_complexity(self, query)` (line 243)
- `get_selection_stats(self)` (line 296)

### `cognitive/multi_agent_roles.py`

**class `Role`** (line 83)
- `from_string(cls, value)` (line 98)

**class `RoleConfig`** (line 119)
- `to_dict(self)` (line 132)

**class `Task`** (line 315)
- `to_dict(self)` (line 332)

**class `Handoff`** (line 338)
- `to_dict(self)` (line 352)

**class `TerminalRegistration`** (line 358)
- `to_dict(self)` (line 371)

**class `Session`** (line 383)
- `to_dict(self)` (line 396)

**class `CoordinatorStatus`** (line 409)
- `to_dict(self)` (line 424)

**class `MultiAgentCoordinator`** (line 446)
- `__init__(self, state_dir, auto_save)` (line 474)
- `_generate_id(self, prefix)` (line 499)
- `_load_state(self)` (line 504)
- `_save_state(self)` (line 532)
- `start_session(self, roles)` (line 554)
- `end_session(self)` (line 585)
- `register_terminal(self, role, pid)` (line 623)
- `unregister_terminal(self, terminal_id)` (line 669)
- `assign_task(self, role, description, context)` (line 689)
- `get_next_task(self, role)` (line 724)
- `get_tasks_for_role(self, role, status)` (line 745)
- `complete_task(self, task_id, output)` (line 768)
- `handoff(self, from_role, to_role, note, context)` (line 801)
- `get_shared_context(self)` (line 865)
- `add_shared_context(self, key, value)` (line 885)
- `get_status(self)` (line 901)
- `get_role_config(self, role)` (line 919)
- `get_role_prompt(self, role)` (line 936)
- `list_roles(self)` (line 948)

### `cognitive/personality.py`

**class `SamMode`** (line 25)
- *(no methods)*

**class `PersonalityTrait`** (line 80)
- *(no methods)*

### `cognitive/planning_framework.py`

**class `SolutionTier`** (line 43)
- *(no methods)*

**class `Capability`** (line 51)
- *(no methods)*

**class `TierOption`** (line 65)
- `available(self)` (line 77)
- `to_dict(self)` (line 88)

**class `PlanningFramework`** (line 531)
- `__init__(self, options)` (line 542)
- `get_option(self, capability, tier)` (line 552)
- `get_all_options(self, capability)` (line 559)
- `check_tier_availability(self, capability, tier)` (line 566)
- `get_best_available(self, capability)` (line 581)
- `get_available_tier(self, capability)` (line 592)
- `get_all_available(self, capability)` (line 597)
- `generate_system_plan(self)` (line 601)
- `generate_tiered_plan(self)` (line 614)
- `estimate_total_ram(self, plan)` (line 637)
- `get_capability_summary(self, capability)` (line 656)
- `get_system_summary(self)` (line 677)
- `clear_cache(self)` (line 693)

### `cognitive/quality_validator.py`

**class `QualityIssue`** (line 17)
- *(no methods)*

**class `EscalationReason`** (line 29)
- *(no methods)*

**class `QualityAssessment`** (line 40)
- `to_dict(self)` (line 50)

**class `QualityValidator`** (line 63)
- `__init__(self)` (line 141)
- `validate(self, response, original_query, cognitive_confidence)` (line 145)
- `truncate_repetition(self, text, min_repeat_length, max_repeats)` (line 245)
- `clean_stop_tokens(self, response)` (line 293)
- `_calculate_response_confidence(self, response)` (line 305)
- `should_escalate(self, assessment, cognitive_state)` (line 334)
- `get_validation_stats(self)` (line 366)

### `cognitive/resource_manager.py`

**class `ResourceLevel`** (line 29)
- *(no methods)*

**class `VisionTier`** (line 43)
- *(no methods)*

**class `VoiceTier`** (line 51)
- *(no methods)*

**class `VisionModelState`** (line 79)
- `to_dict(self)` (line 90)
- `should_auto_unload(self)` (line 103)

**class `VoiceResourceState`** (line 112)
- `to_dict(self)` (line 130)
- `can_use_quality_voice(self, available_ram_mb)` (line 141)
- `should_use_fallback(self, available_ram_mb)` (line 153)
- `get_recommended_tier(self, available_ram_mb)` (line 170)

**class `ResourceConfig`** (line 191)
- `load_from_file(cls, path)` (line 222)
- `save_to_file(self, path)` (line 237)

**class `ResourceSnapshot`** (line 264)
- `to_dict(self)` (line 276)

**class `OperationResult`** (line 294)
- *(no methods)*

**class `ResourceManager`** (line 306)
- `__new__(cls)` (line 326)
- `__init__(self)` (line 335)
- `get_memory_info(self)` (line 367)
- `get_swap_usage_gb(self)` (line 414)
- `get_disk_free_gb(self, path)` (line 428)
- `can_train(self)` (line 441)
- `get_resource_level(self)` (line 463)
- `get_snapshot(self)` (line 479)
- `get_vision_status(self)` (line 498)
- `can_load_vision_model(self, tier)` (line 524)
- `request_vision_resources(self, tier)` (line 552)
- `notify_vision_loaded(self, tier, model_name, memory_used_mb)` (line 581)
- `notify_vision_used(self)` (line 606)
- `notify_vision_unloaded(self)` (line 617)
- `register_vision_engine(self, engine)` (line 635)
- `_recommend_vision_tier(self)` (line 644)
- `_schedule_auto_unload(self)` (line 663)
- `_auto_unload_callback(self)` (line 678)
- `_trigger_vision_unload(self)` (line 684)
- `force_vision_unload(self)` (line 697)
- `get_voice_status(self)` (line 717)
- `can_use_quality_voice(self)` (line 743)
- `should_use_voice_fallback(self)` (line 754)
- `get_recommended_voice_tier(self)` (line 767)
- `notify_voice_loaded(self, tier, memory_used_mb, rvc_model)` (line 778)
- `notify_voice_used(self)` (line 803)
- `notify_voice_unloaded(self)` (line 809)
- `get_max_tokens_for_level(self, level)` (line 818)
- `can_perform_heavy_operation(self)` (line 830)
- `heavy_operation_context(self)` (line 855)
- `execute_with_limits(self, func)` (line 859)
- `get_stats(self)` (line 922)
- `update_config(self)` (line 941)

**class `HeavyOperationContext`** (line 957)
- `__init__(self, manager)` (line 960)
- `__enter__(self)` (line 964)
- `__exit__(self, exc_type, exc_val, exc_tb)` (line 971)

### `cognitive/self_knowledge_handler.py`

**class `SelfKnowledgeResponse`** (line 62)
- *(no methods)*

### `cognitive/smart_vision.py`

**class `VisionTier`** (line 39)
- *(no methods)*

**class `TaskType`** (line 46)
- *(no methods)*

**class `VisionResult`** (line 91)
- *(no methods)*

**class `ImageAnalysis`** (line 103)
- *(no methods)*

**class `VisionMemory`** (line 118)
- `__init__(self, db_path)` (line 121)
- `_init_db(self)` (line 125)
- `get_cached(self, image_hash, task_type)` (line 144)
- `cache_result(self, image_hash, task_type, prompt, response, tier_used, confidence)` (line 168)
- `get_stats(self)` (line 180)

**class `SmartVisionRouter`** (line 511)
- `__init__(self)` (line 514)
- `classify_task(self, prompt)` (line 517)
- `get_tier_for_task(self, task_type)` (line 535)
- `process(self, image_path, prompt, force_tier, skip_cache)` (line 539)
- `progressive_analyze(self, image_path, prompt)` (line 627)

### `cognitive/test_cognitive_system.py`

**class `TestResult`** (line 30)
- *(no methods)*

**class `CognitiveTestSuite`** (line 39)
- `__init__(self, verbose)` (line 50)
- `cleanup(self)` (line 57)
- `run_all(self)` (line 64)
- `_print_group_header(self, name)` (line 196)
- `_print_summary(self)` (line 202)
- `_record(self, name, passed, message, duration_ms, category)` (line 235)
- `_time_test(self, func)` (line 243)
- `test_all_imports(self)` (line 254)
- `test_version(self)` (line 285)
- `test_wm_initialization(self)` (line 295)
- `test_wm_add_items(self)` (line 306)
- `test_wm_importance_scoring(self)` (line 319)
- `test_wm_focus_tracking(self)` (line 337)
- `test_wm_context_retrieval(self)` (line 351)
- `test_procedural_skill_storage(self)` (line 370)
- `test_procedural_skill_retrieval(self)` (line 387)
- `test_decay_tracking(self)` (line 409)
- `test_decay_weak_memories(self)` (line 422)
- `test_compression_ratio(self)` (line 439)
- `test_compression_phrase_replacement(self)` (line 453)
- `test_compression_token_scoring(self)` (line 467)
- `test_contextual_compression(self)` (line 481)
- `test_metacognition_confidence(self)` (line 499)
- `test_metacognition_factors(self)` (line 511)
- `test_goal_creation(self)` (line 524)
- `test_goal_hierarchy(self)` (line 537)
- `test_goal_progress(self)` (line 551)
- `test_attention_focus(self)` (line 567)
- `test_reasoning_steps(self)` (line 580)
- `test_mood_states(self)` (line 596)
- `test_mood_triggers(self)` (line 607)
- `test_mood_transitions(self)` (line 619)
- `test_response_modulation(self)` (line 634)
- `test_relationship_tracking(self)` (line 647)
- `test_active_learner(self)` (line 665)
- `test_predictive_cache(self)` (line 681)
- `test_mlx_availability(self)` (line 698)
- `test_model_selector_context(self)` (line 705)
- `test_model_selector_complexity(self)` (line 718)
- `test_model_selector_task_types(self)` (line 734)
- `test_token_budget_allocation(self)` (line 747)
- `test_token_budget_compression(self)` (line 761)
- `test_quality_validator_good(self)` (line 777)
- `test_quality_validator_repetition(self)` (line 790)
- `test_quality_validator_uncertainty(self)` (line 804)
- `test_quality_validator_escalation(self)` (line 817)
- `test_confidence_factual(self)` (line 831)
- `test_confidence_complex(self)` (line 843)
- `test_confidence_uncertain(self)` (line 856)
- `test_orchestrator_init(self)` (line 873)
- `test_orchestrator_simple_query(self)` (line 888)
- `test_orchestrator_complex_query(self)` (line 911)
- `test_orchestrator_conversation(self)` (line 932)
- `test_orchestrator_state(self)` (line 956)
- `test_memory_emotional_integration(self)` (line 976)
- `test_cognitive_mlx_integration(self)` (line 996)
- `test_compression_performance(self)` (line 1023)
- `test_model_selection_performance(self)` (line 1041)

### `cognitive/test_e2e_comprehensive.py`

**class `TestResult`** (line 50)
- *(no methods)*

**class `TestReport`** (line 60)
- `total_tests(self)` (line 67)
- `passed_tests(self)` (line 71)
- `failed_tests(self)` (line 75)
- `pass_rate(self)` (line 79)
- `total_duration_ms(self)` (line 85)
- `to_dict(self)` (line 88)

**class `TestAPIContracts`** (line 154)
- `test_health_endpoint_contract(self, api_client, server_available)` (line 157)
- `test_resources_endpoint_contract(self, api_client, server_available)` (line 174)
- `test_cognitive_state_endpoint_contract(self, api_client, server_available)` (line 206)
- `test_cognitive_mood_endpoint_contract(self, api_client, server_available)` (line 225)
- `test_cognitive_process_endpoint_contract(self, api_client, server_available)` (line 243)
- `test_vision_models_endpoint_contract(self, api_client, server_available)` (line 270)

**class `TestIntegration`** (line 291)
- `test_simple_math_query(self, api_client, server_available)` (line 294)
- `test_greeting_response(self, api_client, server_available)` (line 316)
- `test_factual_query(self, api_client, server_available)` (line 338)
- `test_state_persists_across_queries(self, api_client, server_available)` (line 358)
- `test_mood_changes_with_interaction(self, api_client, server_available)` (line 384)

**class `TestStreaming`** (line 411)
- `test_streaming_endpoint_responds(self, api_client, server_available)` (line 414)
- `test_streaming_token_by_token(self, api_client, server_available)` (line 467)

**class `TestResourceManagement`** (line 521)
- `test_resources_report_memory(self, api_client, server_available)` (line 524)
- `test_resource_level_affects_tokens(self, api_client, server_available)` (line 543)
- `test_heavy_op_flag_accurate(self, api_client, server_available)` (line 568)

**class `TestPersonality`** (line 592)
- `test_response_has_personality(self, api_client, server_available)` (line 595)
- `test_response_not_empty(self, api_client, server_available)` (line 625)
- `test_mood_influences_response(self, api_client, server_available)` (line 650)

**class `TestLoad`** (line 677)
- `test_concurrent_health_checks(self, api_client, server_available)` (line 680)
- `test_rapid_sequential_queries(self, api_client, server_available)` (line 711)

**class `TestChaos`** (line 749)
- `test_empty_query_handled(self, api_client, server_available)` (line 752)
- `test_very_long_query_handled(self, api_client, server_available)` (line 768)
- `test_special_characters_handled(self, api_client, server_available)` (line 786)
- `test_invalid_json_handled(self, api_client, server_available)` (line 819)
- `test_missing_user_id_handled(self, api_client, server_available)` (line 836)

**class `TestPerformance`** (line 857)
- `test_health_latency(self, api_client, server_available)` (line 860)
- `test_cognitive_latency_warm(self, api_client, server_available)` (line 874)
- `test_resources_endpoint_fast(self, api_client, server_available)` (line 902)

**class `TestRegression`** (line 921)
- `test_server_starts(self, api_client, server_available)` (line 924)
- `test_cognitive_system_loads(self, api_client, server_available)` (line 933)
- `test_can_generate_response(self, api_client, server_available)` (line 945)

### `cognitive/test_vision_system.py`

**class `TestResult`** (line 29)
- *(no methods)*

**class `VisionTestSuite`** (line 38)
- `__init__(self, verbose)` (line 50)
- `_create_test_image(self)` (line 60)
- `cleanup(self)` (line 87)
- `run_all(self)` (line 94)
- `_time_test(self, func)` (line 203)
- `_record(self, name, passed, message, duration, category)` (line 216)
- `test_all_imports(self)` (line 227)
- `test_version(self)` (line 248)
- `test_vision_config_creation(self)` (line 257)
- `test_engine_initialization(self)` (line 274)
- `test_engine_stats(self)` (line 284)
- `test_selector_initialization(self)` (line 299)
- `test_selector_detect_task_type(self)` (line 309)
- `test_selector_estimate_complexity(self)` (line 321)
- `test_selector_select_model(self)` (line 335)
- `test_validator_initialization(self)` (line 354)
- `test_validator_good_response(self)` (line 364)
- `test_validator_bad_response(self)` (line 379)
- `test_task_type_enum(self)` (line 398)
- `test_task_type_caption(self)` (line 411)
- `test_task_type_detection(self)` (line 421)
- `test_task_type_reasoning(self)` (line 431)
- `test_result_creation(self)` (line 445)
- `test_result_to_dict(self)` (line 463)
- `test_orchestrator_vision_engine(self)` (line 486)
- `test_orchestrator_describe_method(self)` (line 502)
- `test_orchestrator_detect_method(self)` (line 517)
- `test_orchestrator_answer_method(self)` (line 532)
- `test_create_vision_engine(self)` (line 551)
- `test_vision_models_constant(self)` (line 565)
- `test_vision_models_smolvlm(self)` (line 574)
- `test_vision_models_moondream(self)` (line 585)

### `cognitive/token_budget.py`

**class `TokenBudget`** (line 13)
- `remaining_for_generation(self)` (line 23)
- `utilization(self)` (line 29)
- `is_valid(self)` (line 34)
- `to_dict(self)` (line 38)

**class `TokenBudgetManager`** (line 52)
- `__init__(self)` (line 94)
- `allocate(self, model_key, system_prompt, context, query, compressor)` (line 98)
- `count_tokens(self, text)` (line 170)
- `estimate_tokens_needed(self, system_prompt, context, query, expected_response_length)` (line 182)
- `get_model_for_budget(self, system_prompt, context, query, preferred_model)` (line 197)
- `_truncate_to_tokens(self, text, max_tokens)` (line 222)
- `get_allocation_stats(self)` (line 236)

### `cognitive/ui_awareness.py`

**class `UIState`** (line 75)
- *(no methods)*

**class `UIElement`** (line 86)
- *(no methods)*

**class `AppState`** (line 101)
- *(no methods)*

**class `UIVerifier`** (line 399)
- `__init__(self)` (line 412)
- `get_app_state(self, app_name)` (line 424)
- `verify_contains(self, app_name, text)` (line 479)
- `verify_no_errors(self, app_name)` (line 491)
- `verify_ready(self, app_name)` (line 501)
- `wait_for_state(self, app_name, target_state, timeout, poll_interval)` (line 509)
- `wait_for_text(self, app_name, text, timeout, poll_interval)` (line 524)
- `wait_for_no_loading(self, app_name, timeout, poll_interval)` (line 538)
- `click_button(self, app_name, button_name)` (line 553)
- `type_text(self, app_name, text)` (line 589)
- `watch(self, app_name, callback, interval, duration)` (line 608)

**class `SAMUIAwareness`** (line 630)
- `__init__(self)` (line 637)
- `check_action_result(self, app_name, expected_outcome)` (line 641)
- `verify_before_responding(self, app_name, claim)` (line 696)
- `get_real_situation(self, app_name)` (line 720)

### `cognitive/unified_orchestrator.py`

**class `ImageContext`** (line 98)
- `__post_init__(self)` (line 115)
- `to_dict(self)` (line 119)
- `get_context_string(self, max_chars)` (line 131)

**class `RAGStats`** (line 258)
- `to_dict(self)` (line 274)
- `get_source_summary(self, max_sources)` (line 285)

**class `CognitiveResponse`** (line 321)
- *(no methods)*

**class `VisionResponse`** (line 333)
- *(no methods)*

**class `CognitiveOrchestrator`** (line 344)
- `__init__(self, db_path, retrieval_db_paths)` (line 366)
- `_build_system_prompt(self)` (line 451)
- `_load_user_facts(self, user_id)` (line 464)
- `get_user_facts_context(self, user_id, max_tokens)` (line 496)
- `set_user(self, user_id)` (line 528)
- `_detect_startup_project(self)` (line 539)
- `_load_project_profile(self, project_name)` (line 574)
- `set_project(self, path)` (line 598)
- `_check_session_recall(self)` (line 651)
- `get_pending_recall(self)` (line 691)
- `handle_recall_query(self, query)` (line 704)
- `get_project_context_text(self)` (line 739)
- `get_last_session_summary(self)` (line 825)
- `save_project_session(self, working_on, notes)` (line 860)
- `process(self, user_input, user_id)` (line 873)
- `_build_context(self, user_input, retrieved, working_memory, emotional_context, user_id)` (line 1037)
- `_build_rag_stats(self, query, retrieved_chunks)` (line 1134)
- `_generate_response(self, query, context, cognitive_result)` (line 1242)
- `_generate_response_placeholder(self, query, context)` (line 1291)
- `vision_engine(self)` (line 1299)
- `process_image(self, image_path, prompt, task, model)` (line 1305)
- `describe_image(self, image_path, detail_level)` (line 1362)
- `detect_objects(self, image_path, target)` (line 1381)
- `answer_about_image(self, image_path, question)` (line 1398)
- `_compute_image_hash(self, image_path)` (line 1415)
- `set_image_context(self, image_path, description, task_type, user_id, metadata)` (line 1427)
- `get_image_context(self)` (line 1465)
- `clear_image_context(self)` (line 1484)
- `has_image_context(self)` (line 1490)
- `is_image_followup(self, query)` (line 1494)
- `process_image_followup(self, query, user_id)` (line 1506)
- `process_with_image(self, user_input, image_path, user_id)` (line 1560)
- `create_goal(self, description, priority)` (line 1691)
- `update_goal_progress(self, goal_id, progress)` (line 1698)
- `get_learning_suggestions(self, n)` (line 1702)
- `get_state(self)` (line 1706)
- `run_maintenance(self)` (line 1720)
- `shutdown(self)` (line 1732)

### `cognitive/vision_client.py`

**class `VisionTier`** (line 47)
- *(no methods)*

**class `VisionResponse`** (line 56)
- `from_api_response(cls, data)` (line 72)
- `to_dict(self)` (line 89)

**class `VisionClient`** (line 107)
- `__init__(self, base_url, timeout)` (line 130)
- `_get_session(self)` (line 146)
- `_post(self, endpoint, data)` (line 153)
- `_get(self, endpoint, params)` (line 171)
- `_prepare_image(self, image)` (line 185)
- `process(self, image, prompt, model)` (line 201)
- `describe(self, image, detail_level)` (line 231)
- `detect(self, image, target)` (line 256)
- `ocr(self, image)` (line 282)
- `smart(self, image, prompt, force_tier, skip_cache)` (line 303)
- `get_models(self)` (line 342)
- `get_stats(self)` (line 356)
- `get_smart_stats(self)` (line 369)
- `health_check(self)` (line 378)
- `close(self)` (line 396)
- `__enter__(self)` (line 402)
- `__exit__(self, exc_type, exc_val, exc_tb)` (line 405)

**class `DirectVisionClient`** (line 409)
- `__init__(self)` (line 424)
- `_get_engine(self)` (line 429)
- `_get_smart_router(self)` (line 436)
- `process(self, image, prompt, model)` (line 443)
- `describe(self, image, detail_level)` (line 508)
- `detect(self, image, target)` (line 522)
- `ocr(self, image)` (line 534)
- `smart(self, image, prompt, force_tier, skip_cache)` (line 581)
- `get_stats(self)` (line 637)
- `get_smart_stats(self)` (line 642)
- `unload_models(self)` (line 647)

### `cognitive/vision_engine.py`

**class `VisionTaskType`** (line 151)
- *(no methods)*

**class `VisionConfig`** (line 162)
- *(no methods)*

**class `VisionResult`** (line 172)
- `to_dict(self)` (line 184)

**class `ModelSelection`** (line 199)
- *(no methods)*

**class `MLXVisionLoader`** (line 221)
- `__init__(self)` (line 227)
- `mlx_available(self)` (line 240)
- `_update_last_used(self)` (line 243)
- `is_model_loaded(self)` (line 249)
- `get_idle_seconds(self)` (line 258)
- `schedule_unload(self, timeout_seconds)` (line 264)
- `unload_model(self)` (line 306)
- `set_auto_unload(self, enabled, timeout_seconds)` (line 338)
- `load_model(self, model_key, try_fallbacks)` (line 357)
- `get_current_model(self)` (line 436)
- `unload_all(self)` (line 439)

**class `VisionModelSelector`** (line 462)
- `__init__(self, max_memory_mb)` (line 499)
- `detect_task_type(self, prompt)` (line 506)
- `estimate_complexity(self, prompt)` (line 516)
- `get_available_memory_mb(self)` (line 556)
- `select_model(self, prompt, image_size, force_model, confidence_required)` (line 567)

**class `VisionQualityValidator`** (line 684)
- `validate(self, response, prompt, task_type)` (line 704)

**class `VisionEngine`** (line 782)
- `__init__(self, adapter_path, max_memory_mb)` (line 794)
- `process_image(self, image_source, prompt, config)` (line 813)
- `_process_via_subprocess(self, image_path, prompt, selection, config, start_time)` (line 884)
- `_process_via_server(self, image_path, prompt, selection, config, start_time)` (line 975)
- `_process_local(self, image_source, prompt, selection, config, start_time)` (line 1030)
- `_process_local_direct(self, image_source, prompt, selection, config, start_time)` (line 1051)
- `_escalate_to_claude(self, image_source, prompt, selection, start_time, error)` (line 1115)
- `_send_to_claude(self, image_source, prompt)` (line 1159)
- `_resolve_image(self, image_source, preprocess)` (line 1195)
- `get_stats(self)` (line 1250)
- `unload_models(self)` (line 1267)
- `is_model_loaded(self)` (line 1271)
- `schedule_unload(self, timeout_seconds)` (line 1279)
- `set_auto_unload(self, enabled, timeout_seconds)` (line 1290)
- `get_idle_seconds(self)` (line 1303)

### `cognitive/vision_selector.py`

**class `VisionTier`** (line 101)
- *(no methods)*

**class `TierCapabilities`** (line 110)
- *(no methods)*

**class `SelectionContext`** (line 158)
- *(no methods)*

**class `TierSelection`** (line 169)
- *(no methods)*

**class `TierSuccessTracker`** (line 183)
- `__init__(self, db_path)` (line 190)
- `_init_db(self)` (line 194)
- `record_result(self, tier, task_type, success, latency_ms, memory_gb)` (line 217)
- `get_success_rate(self, tier, task_type, hours)` (line 242)
- `get_average_latency(self, tier, task_type)` (line 274)
- `get_stats(self)` (line 297)

**class `VisionSelector`** (line 326)
- `__init__(self)` (line 351)
- `_classify_task_type(self, prompt)` (line 356)
- `_classify_complexity(self, prompt)` (line 386)
- `_get_viable_tiers(self, available_ram_gb, task_type)` (line 405)
- `_apply_success_weighting(self, tiers, task_type)` (line 452)
- `_apply_time_constraint(self, weighted_tiers, time_constraint_ms)` (line 502)
- `select_tier(self, task_type, available_ram_gb, complexity, time_constraint_ms, previous_tier_failed)` (line 526)
- `get_recommended_tier(self, image_path, prompt, time_constraint_ms)` (line 640)
- `_looks_like_text_image(self, image_path)` (line 684)
- `record_tier_result(self, tier, task_type, success, latency_ms)` (line 707)
- `get_stats(self)` (line 718)

### `execution/auto_fix.py`

**class `AutoFixableIssue`** (line 54)
- `description(self)` (line 67)
- `safe_to_auto_fix(self)` (line 82)

**class `DetectedIssue`** (line 95)
- `__hash__(self)` (line 122)
- `to_dict(self)` (line 125)

**class `FixResult`** (line 142)
- `to_dict(self)` (line 161)

**class `AutoFixProposal`** (line 174)
- `format_for_display(self)` (line 193)

**class `ToolChecker`** (line 237)
- `is_available(cls, tool)` (line 243)
- `get_available_tools(cls)` (line 250)

**class `IssueDetector`** (line 266)
- `__init__(self, verbose)` (line 279)
- `_log(self, message)` (line 288)
- `detect_issues(self, file_path)` (line 293)
- `detect_project_issues(self, project_path)` (line 324)
- `_detect_python_issues(self, path)` (line 378)
- `_run_ruff(self, path)` (line 396)
- `_run_ruff_project(self, project_path)` (line 446)
- `_ruff_rule_to_type(self, rule)` (line 491)
- `_check_black_formatting(self, path)` (line 506)
- `_check_isort(self, path)` (line 538)
- `_detect_javascript_issues(self, path)` (line 569)
- `_run_eslint(self, path)` (line 581)
- `_run_eslint_project(self, project_path)` (line 622)
- `_check_prettier(self, path)` (line 663)
- `_detect_rust_issues(self, path)` (line 694)
- `_check_rustfmt(self, path)` (line 704)
- `_detect_swift_issues(self, path)` (line 735)
- `_check_swift_format(self, path)` (line 744)
- `_detect_whitespace_issues(self, path)` (line 781)

**class `ExecutionHistory`** (line 825)
- `__init__(self)` (line 828)
- `_load(self)` (line 839)
- `_save(self)` (line 849)
- `record(self, result)` (line 854)
- `get_stats(self)` (line 878)
- `get_recent(self, limit)` (line 894)

**class `AutoFixer`** (line 899)
- `__init__(self, create_backups, verbose)` (line 918)
- `_log(self, message)` (line 935)
- `_create_backup(self, file_path)` (line 940)
- `fix_issue(self, issue)` (line 971)
- `_run_fix_command(self, issue)` (line 1022)
- `_apply_builtin_fix(self, issue)` (line 1049)
- `fix_all_in_file(self, file_path)` (line 1098)
- `_fix_python_file(self, path, backup_path)` (line 1137)
- `_fix_javascript_file(self, path, backup_path)` (line 1229)
- `_fix_rust_file(self, path, backup_path)` (line 1295)
- `_fix_swift_file(self, path, backup_path)` (line 1331)
- `fix_all_in_project(self, project_path)` (line 1367)
- `dry_run(self, issue)` (line 1442)
- `create_proposal(self, path, include_non_fixable)` (line 1499)

### `execution/auto_fix_control.py`

**class `AutoFixableIssue`** (line 75)
- *(no methods)*

**class `FixResultStatus`** (line 120)
- *(no methods)*

**class `DetectedIssue`** (line 132)
- `to_dict(self)` (line 161)
- `from_dict(cls, data)` (line 166)

**class `FixResult`** (line 172)
- `to_dict(self)` (line 196)
- `from_dict(cls, data)` (line 201)

**class `AutoFixPermissions`** (line 207)
- `to_dict(self)` (line 258)
- `from_dict(cls, data)` (line 263)
- `is_fix_type_allowed(self, fix_type)` (line 267)
- `is_file_allowed(self, file_path)` (line 275)

**class `RateLimitStatus`** (line 296)
- `__post_init__(self)` (line 317)
- `to_dict(self)` (line 321)

**class `AutoFixStats`** (line 335)
- `to_dict(self)` (line 363)

**class `AutoFixTracker`** (line 457)
- `__init__(self, db_path)` (line 469)
- `_init_db(self)` (line 479)
- `_get_conn(self)` (line 487)
- `track_success(self, project_id, issue, result)` (line 491)
- `track_failure(self, project_id, issue, error)` (line 537)
- `track_revert(self, project_id, issue, reason)` (line 576)
- `track_skip(self, project_id, issue, reason)` (line 621)
- `get_issue_history(self, file_path, limit)` (line 664)
- `should_skip_file(self, file_path, failure_threshold, window_hours)` (line 710)
- `save_detected_issue(self, project_id, issue)` (line 763)
- `get_pending_issues(self, project_id, limit)` (line 800)

**class `AutoFixController`** (line 865)
- `__init__(self, db_path)` (line 877)
- `_init_db(self)` (line 888)
- `_get_conn(self)` (line 896)
- `get_permissions(self, project_id)` (line 900)
- `save_permissions(self, permissions)` (line 929)
- `can_auto_fix(self, project_id, issue)` (line 955)
- `_get_file_fix_count(self, project_id, file_path)` (line 1019)
- `_increment_file_fix_count(self, project_id, file_path)` (line 1039)
- `should_require_review(self, project_id, issues)` (line 1059)
- `get_rate_limit_status(self, project_id)` (line 1097)
- `_increment_rate_limit(self, project_id)` (line 1137)
- `record_fix(self, project_id, issue, result)` (line 1157)
- `get_fix_stats(self, project_id)` (line 1189)
- `get_pending_issues(self, project_id, limit)` (line 1306)
- `cleanup_old_data(self, days_to_keep)` (line 1323)

### `execution/command_classifier.py`

**class `CommandType`** (line 34)
- *(no methods)*

**class `RiskLevel`** (line 56)
- *(no methods)*

**class `ClassificationResult`** (line 65)
- *(no methods)*

**class `CommandClassifier`** (line 550)
- `__init__(self, custom_trusted_hosts)` (line 563)
- `classify(self, command)` (line 585)
- `classify_detailed(self, command)` (line 598)
- `is_safe(self, command)` (line 742)
- `get_dangers(self, command)` (line 755)
- `get_reasoning(self, command)` (line 768)
- `_extract_base_command(self, command)` (line 781)
- `_extract_env_vars(self, command)` (line 810)
- `_has_command_chaining(self, command)` (line 817)
- `_extract_paths(self, command)` (line 837)
- `_determine_type(self, command, base_cmd)` (line 853)
- `_check_network_operations(self, command)` (line 899)

### `execution/command_proposer.py`

**class `CommandProposal`** (line 107)
- `__post_init__(self)` (line 142)
- `_is_safe_command(self)` (line 157)
- `to_dict(self)` (line 173)
- `from_dict(cls, data)` (line 192)

**class `ExecutionResult`** (line 220)
- `to_dict(self)` (line 236)

**class `CommandProposer`** (line 241)
- `__init__(self, classifier)` (line 265)
- `_init_classifier(self)` (line 276)
- `_load_patterns(self)` (line 284)
- `_classify_command(self, command)` (line 358)
- `_assess_risk(self, command, command_type)` (line 399)
- `propose_fix(self, problem_description, context)` (line 427)
- `propose_for_task(self, task, project_context)` (line 516)

**class `ProposalFormatter`** (line 717)
- `format_for_chat(proposal)` (line 738)
- `format_for_gui(proposal)` (line 810)
- `format_compact(proposal)` (line 857)
- `_extract_risk_level(risk_assessment)` (line 880)
- `_risk_to_color(risk_level)` (line 896)
- `_get_actions(proposal)` (line 908)
- `format_execution_result(result)` (line 957)

**class `ProposalHistory`** (line 1015)
- `__init__(self, history_file, feedback_file)` (line 1023)
- `_load_history(self)` (line 1038)
- `_save_history(self)` (line 1047)
- `_load_feedback(self)` (line 1051)
- `_save_feedback(self)` (line 1060)
- `record_proposal(self, proposal)` (line 1064)
- `record_outcome(self, proposal_id, accepted, result, feedback)` (line 1077)
- `_record_feedback_pattern(self, proposal, accepted, result, feedback)` (line 1108)
- `_update_patterns(self)` (line 1156)
- `get_pattern_score(self, problem_type, cmd_type)` (line 1171)
- `get_pending_proposals(self)` (line 1188)
- `get_recent_proposals(self, limit)` (line 1195)
- `get_statistics(self)` (line 1204)
- `clear_old_proposals(self, days)` (line 1219)

### `execution/escalation_handler.py`

**class `EscalationReason`** (line 74)
- *(no methods)*

**class `SAMResponse`** (line 85)
- *(no methods)*

### `execution/escalation_learner.py`

**class `Escalation`** (line 78)
- *(no methods)*

**class `TaskPattern`** (line 90)
- *(no methods)*

**class `EscalationDB`** (line 102)
- `__init__(self, db_path)` (line 103)
- `_init_db(self)` (line 108)
- `add_escalation(self, escalation)` (line 170)
- `add_local_attempt(self, query, task_type, confidence, success)` (line 208)
- `find_similar_escalations(self, query_hash, limit)` (line 242)
- `get_task_pattern(self, task_type)` (line 257)
- `get_unlearned_escalations(self, limit)` (line 288)
- `mark_as_learned(self, escalation_ids)` (line 302)
- `get_stats(self)` (line 312)

**class `EscalationLearner`** (line 367)
- `__init__(self)` (line 368)
- `classify_task(self, query)` (line 371)
- `should_escalate(self, query, local_confidence)` (line 397)
- `log_escalation(self, query, response, task_type, tokens_used, model)` (line 425)
- `log_local_success(self, query, confidence, success)` (line 461)
- `export_training_data(self, output_path)` (line 466)
- `get_stats(self)` (line 495)
- `print_stats(self)` (line 499)

### `execution/execution_history.py`

**class `CheckpointStatus`** (line 58)
- *(no methods)*

**class `ExecutionStatus`** (line 65)
- *(no methods)*

**class `ExecutionResult`** (line 74)
- `to_dict(self)` (line 90)
- `from_dict(cls, data)` (line 101)

**class `CommandLog`** (line 113)
- `to_dict(self)` (line 127)
- `from_dict(cls, data)` (line 137)

**class `Checkpoint`** (line 148)
- `to_dict(self)` (line 170)
- `from_dict(cls, data)` (line 184)

**class `CheckpointInfo`** (line 199)
- `to_dict(self)` (line 221)

**class `RollbackResult`** (line 236)
- `to_dict(self)` (line 252)

**class `ExecutionStats`** (line 264)
- `to_dict(self)` (line 286)

**class `RollbackManager`** (line 300)
- `__init__(self, base_dir)` (line 328)
- `_init_db(self)` (line 350)
- `create_checkpoint(self, project_id, description)` (line 389)
- `add_file_backup(self, checkpoint_id, file_path)` (line 444)
- `add_command_log(self, checkpoint_id, command, result)` (line 529)
- `rollback(self, checkpoint_id)` (line 580)
- `list_checkpoints(self, project_id, limit)` (line 672)
- `get_checkpoint_details(self, checkpoint_id)` (line 728)
- `cleanup_old_checkpoints(self, days)` (line 771)

**class `ExecutionLogger`** (line 828)
- `__init__(self, base_dir)` (line 854)
- `_init_db(self)` (line 874)
- `_detect_command_type(self, command)` (line 923)
- `log_execution(self, approval_id, command, result, duration_ms, project_id)` (line 967)
- `get_recent_executions(self, limit)` (line 1032)
- `get_executions_by_project(self, project_id, limit)` (line 1063)
- `get_execution_stats(self)` (line 1095)
- `export_to_json(self, start_date, end_date)` (line 1167)
- `mark_as_rolled_back(self, approval_id)` (line 1217)

### `execution/safe_executor.py`

**class `ExecutionStatus`** (line 156)
- *(no methods)*

**class `ExecutionResult`** (line 166)
- `to_dict(self)` (line 180)

**class `FileOperationResult`** (line 188)
- *(no methods)*

**class `ExecutionContext`** (line 199)
- `__post_init__(self)` (line 213)

**class `RollbackInfo`** (line 221)
- *(no methods)*

**class `FileOperation`** (line 236)
- `__init__(self, backup_dir)` (line 239)
- `_cleanup_old_backups(self)` (line 249)
- `_generate_backup_name(self, original_path)` (line 260)
- `_validate_path(self, path, allowed_paths)` (line 273)
- `read_file(self, path, allowed_paths)` (line 299)
- `write_file(self, path, content, allowed_paths, max_size_mb)` (line 333)
- `create_backup(self, path)` (line 409)
- `restore_backup(self, backup_path, original_path)` (line 444)
- `list_backups(self, original_path)` (line 483)

**class `SafeExecutor`** (line 518)
- `__init__(self)` (line 521)
- `_build_safe_environment(self, context, base_env)` (line 527)
- `_validate_working_directory(self, working_dir, allowed_paths)` (line 570)
- `_check_command_safety(self, command)` (line 606)
- `_set_resource_limits(self, max_memory_mb)` (line 635)
- `_log_execution(self, command, context, result)` (line 662)
- `execute(self, command, working_dir, timeout, context)` (line 694)
- `execute_with_rollback_info(self, command, working_dir, timeout, context)` (line 870)
- `get_stats(self)` (line 918)

### `memory/context_budget.py`

**class `SectionPriority`** (line 20)
- *(no methods)*

**class `ContextSection`** (line 35)
- `effective_priority(self)` (line 54)
- `__lt__(self, other)` (line 65)

**class `QueryType`** (line 70)
- *(no methods)*

**class `SectionBudget`** (line 81)
- `__post_init__(self)` (line 88)

**class `BudgetAllocation`** (line 93)
- `to_dict(self)` (line 104)
- `remaining(self)` (line 116)

**class `ContextBudget`** (line 126)
- `__init__(self, default_budget)` (line 266)
- `detect_query_type(self, query)` (line 276)
- `allocate(self, query_type, available_tokens, custom_priorities)` (line 343)
- `fit_content(self, section, content, max_tokens, preserve_start, preserve_end)` (line 409)
- `_truncate_preserve_start(self, content, target_chars)` (line 464)
- `_truncate_preserve_end(self, content, target_chars)` (line 488)
- `_truncate_rag_results(self, content, target_chars)` (line 514)
- `get_rag_budget(self, total_budget, query_type, consumed_by_other_sections)` (line 557)
- `count_tokens(self, text)` (line 597)
- `tokens_to_chars(self, tokens)` (line 611)
- `get_section_priority(self, section_type, query_type, relevance_score)` (line 615)
- `order_context_sections(self, sections, query, query_type)` (line 655)
- `_distribute_middle_sections(self, sections)` (line 738)
- `create_context_section(self, name, content, relevance_score, query_type)` (line 779)
- `build_ordered_context(self, sections, query, total_tokens, query_type)` (line 817)
- `get_allocation_stats(self)` (line 915)

**class `ContextBuilder`** (line 951)
- `__init__(self, budget)` (line 958)
- `build(self, query, system_prompt, user_facts, project_context, rag_results, conversation_history, working_memory, total_tokens, query_type)` (line 967)
- `build_ordered(self, query, system_prompt, user_facts, project_context, rag_results, conversation_history, working_memory, total_tokens, query_type)` (line 1105)

**class `ContextType`** (line 1213)
- *(no methods)*

**class `ScoredContent`** (line 1226)
- `__post_init__(self)` (line 1253)
- `__lt__(self, other)` (line 1257)

**class `ContextImportanceScorer`** (line 1262)
- `__init__(self, use_embeddings, usage_history_path, custom_weights)` (line 1335)
- `_load_usage_history(self)` (line 1367)
- `_save_usage_history(self)` (line 1380)
- `_get_content_id(self, content)` (line 1393)
- `_get_embedding(self, text)` (line 1397)
- `_compute_semantic_similarity(self, query, content)` (line 1437)
- `_keyword_similarity(self, query, content)` (line 1456)
- `_compute_recency_score(self, context_type, timestamp)` (line 1467)
- `_compute_reliability_score(self, context_type, source, metadata)` (line 1498)
- `_compute_usage_score(self, content_id)` (line 1534)
- `record_usage(self, content_id, was_helpful)` (line 1571)
- `score_content(self, content, query, context_type, timestamp, source, metadata)` (line 1595)
- `rank_contents(self, contents, query, return_scored)` (line 1650)
- `should_include(self, content, query, context_type, score_threshold)` (line 1732)
- `allocate_token_budget(self, contents, query, total_budget)` (line 1756)
- `select_for_budget(self, contents, query, token_budget, score_threshold)` (line 1813)
- `refresh_timestamp(self)` (line 1849)

**class `AdaptiveSection`** (line 1871)
- `get_allocation(self, total_budget)` (line 1892)

**class `AdaptiveContextManager`** (line 1906)
- `__init__(self, context_budget, default_budget)` (line 2063)
- `get_adaptive_sections(self, query, query_type, available_sections)` (line 2079)
- `adapt_budget(self, query_type, total_budget, available_sections, custom_overrides)` (line 2134)
- `get_section_config(self, query_type, section_name)` (line 2235)
- `build_adaptive_context(self, query, sections, total_budget, query_type)` (line 2263)
- `get_query_type_summary(self, query_type)` (line 2358)
- `get_adaptation_stats(self)` (line 2397)

### `memory/conversation_memory.py`

**class `Message`** (line 43)
- *(no methods)*

**class `Fact`** (line 56)
- *(no methods)*

**class `UserPreference`** (line 70)
- *(no methods)*

**class `ConversationMemory`** (line 163)
- `__init__(self, db_path)` (line 166)
- `start_session(self)` (line 171)
- `end_session(self, summary)` (line 186)
- `add_message(self, role, content, metadata)` (line 202)
- `add_image_message(self, image_path, description, user_prompt, metadata)` (line 242)
- `get_last_image_context(self)` (line 310)
- `get_images_in_conversation(self, limit)` (line 339)
- `get_context(self, max_messages, include_images)` (line 378)
- `get_relevant_facts(self, query, limit)` (line 407)
- `get_preferences(self, category)` (line 429)
- `set_preference(self, category, key, value, example)` (line 443)
- `_extract_facts(self, message_id, content)` (line 480)
- `_consolidate_session(self, session_id)` (line 544)
- `build_context_prompt(self, user_message, include_image_context)` (line 589)
- `get_stats(self)` (line 637)

### `memory/fact_memory.py`

**class `FactCategory`** (line 148)
- *(no methods)*

**class `FactSource`** (line 160)
- *(no methods)*

**class `UserFact`** (line 277)
- `to_dict(self)` (line 323)
- `from_dict(cls, data)` (line 328)
- `from_row(cls, row)` (line 333)

**class `FactExtractor`** (line 496)
- `extract(cls, text, user_id)` (line 648)
- `_infer_category(cls, fact_text)` (line 706)

**class `FactMemory`** (line 818)
- `__init__(self, db_path, auto_decay)` (line 827)
- `_init_db(self)` (line 848)
- `_migrate_add_project_id(self, conn)` (line 861)
- `_get_connection(self)` (line 884)
- `_get_metadata(self, key)` (line 894)
- `_set_metadata(self, key, value)` (line 903)
- `_apply_startup_decay(self)` (line 915)
- `_apply_decay_for_elapsed_days(self, days_elapsed)` (line 952)
- `save_fact(self, fact, category, source, confidence, user_id, project_id, subcategory, source_message_id, source_context, metadata)` (line 1029)
- `save_facts(self, facts)` (line 1144)
- `get_fact(self, fact_id)` (line 1167)
- `get_facts(self, user_id, category, min_confidence, limit, include_inactive)` (line 1180)
- `get_facts_for_context(self, user_id, min_confidence, limit)` (line 1226)
- `search_facts(self, query, user_id, min_confidence, limit)` (line 1276)
- `save_project_fact(self, project_id, fact, category, source, confidence, user_id, subcategory, source_context, metadata)` (line 1318)
- `get_project_facts(self, project_id, min_confidence, category, limit, include_inactive)` (line 1364)
- `get_facts_for_context_with_project(self, user_id, project_id, min_confidence, user_limit, project_limit)` (line 1410)
- `extract_facts_from_text(self, text, user_id, save)` (line 1500)
- `reinforce_fact(self, fact_id, source_message_id)` (line 1528)
- `contradict_fact(self, fact_id, reason)` (line 1584)
- `apply_decay(self, days_threshold)` (line 1641)
- `get_stats(self)` (line 1732)
- `_log_history(self, cur, fact_id, change_type, old_confidence, new_confidence, reason)` (line 1795)
- `_update_accessed(self, fact_ids, reinforce)` (line 1817)
- `deactivate_fact(self, fact_id, reason)` (line 1876)
- `reactivate_fact(self, fact_id)` (line 1899)

### `memory/infinite_context.py`

**class `Domain`** (line 44)
- *(no methods)*

**class `MemoryTier`** (line 54)
- *(no methods)*

**class `StateFragment`** (line 63)
- `touch(self)` (line 74)

**class `Chunk`** (line 81)
- *(no methods)*

**class `GenerationPlan`** (line 93)
- *(no methods)*

**class `StateHandler`** (line 106)
- `extract_state(self, text, existing_state)` (line 110)
- `compress_state(self, state, target_tokens)` (line 115)
- `get_continuation_prompt(self, state, original_prompt, chunk_index)` (line 120)
- `detect_natural_break(self, text)` (line 125)
- `score_coherence(self, prev_chunk, curr_chunk, state)` (line 130)

**class `StoryStateHandler`** (line 135)
- `extract_state(self, text, existing_state)` (line 138)
- `compress_state(self, state, target_tokens)` (line 174)
- `get_continuation_prompt(self, state, original_prompt, chunk_index)` (line 204)
- `detect_natural_break(self, text)` (line 220)
- `score_coherence(self, prev_chunk, curr_chunk, state)` (line 238)

**class `CodeStateHandler`** (line 263)
- `extract_state(self, text, existing_state)` (line 266)
- `compress_state(self, state, target_tokens)` (line 307)
- `get_continuation_prompt(self, state, original_prompt, chunk_index)` (line 327)
- `detect_natural_break(self, text)` (line 346)
- `score_coherence(self, prev_chunk, curr_chunk, state)` (line 371)

**class `AnalysisStateHandler`** (line 390)
- `extract_state(self, text, existing_state)` (line 393)
- `compress_state(self, state, target_tokens)` (line 425)
- `get_continuation_prompt(self, state, original_prompt, chunk_index)` (line 441)
- `detect_natural_break(self, text)` (line 454)
- `score_coherence(self, prev_chunk, curr_chunk, state)` (line 466)

**class `ConversationStateHandler`** (line 478)
- `extract_state(self, text, existing_state)` (line 481)
- `compress_state(self, state, target_tokens)` (line 506)
- `get_continuation_prompt(self, state, original_prompt, chunk_index)` (line 520)
- `detect_natural_break(self, text)` (line 533)
- `score_coherence(self, prev_chunk, curr_chunk, state)` (line 541)

**class `MemoryManager`** (line 550)
- `__init__(self, db_path)` (line 553)
- `_init_db(self)` (line 563)
- `store_working(self, key, value, domain, importance)` (line 607)
- `promote_to_short_term(self, key)` (line 620)
- `store_long_term(self, key, value, domain, importance)` (line 637)
- `recall_long_term(self, domain, limit)` (line 653)
- `store_episode(self, session_id, event_type, content, importance)` (line 679)
- `get_context_for_chunk(self, domain, target_tokens)` (line 692)
- `clear_working(self)` (line 725)

**class `InfiniteContext`** (line 738)
- `__init__(self, domain, model_fn, chunk_size, quality_threshold, max_retries, persistence_path)` (line 756)
- `_default_model(self, prompt)` (line 778)
- `_estimate_needed_chunks(self, prompt)` (line 801)
- `_generate_chunk(self, prompt, chunk_index)` (line 829)
- `generate(self, prompt, max_chunks)` (line 872)
- `stream(self, prompt, max_chunks)` (line 934)
- `_detect_natural_ending(self, text)` (line 966)
- `_merge_chunks(self)` (line 980)
- `save_session(self, output_path)` (line 1002)

### `memory/project_context.py`

**class `ProjectInfo`** (line 281)
- `to_dict(self)` (line 292)
- `__str__(self)` (line 295)

**class `ProjectDetector`** (line 300)
- `__init__(self)` (line 315)
- `detect(self, path)` (line 322)
- `_match_known_project(self, path)` (line 345)
- `_detect_from_markers(self, path)` (line 370)
- `_find_markers(self, path)` (line 403)
- `_infer_language(self, markers)` (line 417)
- `_infer_type(self, markers, language)` (line 425)
- `get_context_string(self, project)` (line 442)

**class `Project`** (line 483)
- *(no methods)*

**class `ProjectSession`** (line 496)
- *(no methods)*

**class `SessionRecallInfo`** (line 511)
- `to_dict(self)` (line 523)

**class `SessionRecall`** (line 537)
- `__init__(self, db_path)` (line 595)
- `get_project_recall(self, project_id, project_name, db_path)` (line 602)
- `_format_time_ago(self, delta)` (line 681)
- `_build_recall_message(self, project_name, working_on, notes, recent_files, time_ago, should_show)` (line 701)
- `is_recall_query(self, query)` (line 741)
- `detect_recall_query_type(self, query)` (line 757)
- `handle_recall_query(self, query, current_project_id, current_project_name, db_path)` (line 773)
- `get_recent_sessions(self, limit, db_path)` (line 902)
- `save_session_state(self, project_id, working_on, notes, recent_files, recent_errors, db_path)` (line 952)

**class `ProjectProfile`** (line 1033)
- `to_context_string(self)` (line 1062)
- `to_dict(self)` (line 1087)

**class `ProjectProfileLoader`** (line 1105)
- `__init__(self, ssot_path)` (line 1136)
- `load_profile(self, project_name)` (line 1142)
- `get_all_profiles(self)` (line 1171)
- `get_profile_names(self)` (line 1184)
- `refresh_cache(self)` (line 1190)
- `_normalize_name(self, name)` (line 1211)
- `_is_cache_valid(self)` (line 1215)
- `_find_profile_file(self, normalized_name)` (line 1221)
- `_parse_profile(self, file_path)` (line 1239)
- `_extract_title(self, content, fallback)` (line 1291)
- `_extract_status(self, content)` (line 1299)
- `_extract_project_path(self, content)` (line 1327)
- `_extract_tech_stack(self, content)` (line 1343)
- `_extract_description(self, content)` (line 1390)
- `_extract_architecture(self, content)` (line 1415)
- `_extract_todos(self, content)` (line 1429)
- `_extract_recent_files(self, content)` (line 1466)
- `_extract_notes(self, content)` (line 1484)
- `_extract_last_session(self, content)` (line 1498)
- `_auto_detect_profile(self, project_name)` (line 1514)

**class `ProjectWatcher`** (line 1566)
- `__init__(self, poll_interval, auto_load_profile)` (line 1603)
- `start(self)` (line 1633)
- `stop(self)` (line 1663)
- `on_project_change(self, callback)` (line 1681)
- `remove_callback(self, callback)` (line 1702)
- `get_current_project(self)` (line 1722)
- `get_current_profile(self)` (line 1732)
- `get_current_path(self)` (line 1742)
- `is_running(self)` (line 1752)
- `check_now(self)` (line 1762)
- `_poll_loop(self)` (line 1773)
- `_check_for_change(self)` (line 1783)
- `get_status(self)` (line 1835)
- `__enter__(self)` (line 1853)
- `__exit__(self, exc_type, exc_val, exc_tb)` (line 1858)

**class `SessionState`** (line 1896)
- `to_dict(self)` (line 1925)
- `from_dict(cls, data)` (line 1939)
- `__str__(self)` (line 1952)

**class `ProjectSessionState`** (line 1966)
- `__init__(self, db_path)` (line 2007)
- `_init_db(self)` (line 2012)
- `save_session(self, project_name, state)` (line 2056)
- `get_last_session(self, project_name)` (line 2091)
- `update_files_touched(self, project_name, files)` (line 2130)
- `add_session_note(self, project_name, note)` (line 2195)
- `get_session_history(self, project_name, limit)` (line 2261)
- `get_all_project_sessions(self)` (line 2300)
- `get_project_notes(self, project_name, limit)` (line 2339)
- `get_recent_activity(self, days, limit)` (line 2372)
- `get_stats(self)` (line 2413)

**class `ProjectContext`** (line 2471)
- `__init__(self, db_path)` (line 2479)
- `_init_db(self)` (line 2485)
- `_load_inventory(self)` (line 2536)
- `detect_project(self, path)` (line 2550)
- `_get_or_create_project(self, path, info)` (line 2567)
- `_detect_from_structure(self, path)` (line 2614)
- `_update_last_accessed(self, project_id)` (line 2646)
- `get_last_session(self, project_id)` (line 2657)
- `save_session_state(self, project_id, working_on, recent_files, recent_errors, notes)` (line 2684)
- `get_project_context(self, project, include_session)` (line 2709)
- `_format_age(self, delta)` (line 2738)
- `get_project_todos(self, project_id, limit)` (line 2748)
- `scan_for_todos(self, project_path, project_id)` (line 2776)
- `get_recent_projects(self, limit)` (line 2825)
- `get_stats(self)` (line 2849)

### `memory/rag_feedback.py`

**class `RAGFeedbackEntry`** (line 85)
- `to_dict(self)` (line 98)
- `from_dict(cls, data)` (line 102)

**class `SourceQualityMetrics`** (line 107)
- `compute_metrics(self)` (line 134)
- `to_dict(self)` (line 186)

**class `ProjectRAGStats`** (line 191)
- *(no methods)*

**class `RAGFeedbackTracker`** (line 310)
- `__init__(self, db_path)` (line 321)
- `_init_db(self)` (line 327)
- `_get_conn(self)` (line 334)
- `record_rag_feedback(self, query, sources, used_source_ids, rating, project_id, response_id)` (line 342)
- `_update_source_quality(self, cur, source_id, file_path, project_id, was_used, rating, timestamp)` (line 446)
- `_update_query_source_effectiveness(self, cur, query_hash, source_id, project_id, was_used, rating, timestamp)` (line 546)
- `_update_project_stats(self, cur, project_id, sources_count, used_count, rating, timestamp)` (line 601)
- `get_source_quality_scores(self, project_id, min_confidence, limit)` (line 669)
- `get_source_quality(self, source_id, project_id)` (line 740)
- `adjust_relevance_score(self, source_id, base_score, project_id, query_hash)` (line 789)
- `batch_adjust_scores(self, results, project_id, query)` (line 862)
- `get_project_stats(self, project_id)` (line 909)
- `get_recent_feedback(self, project_id, limit)` (line 969)
- `get_low_quality_sources(self, project_id, threshold, min_retrievals, limit)` (line 1016)
- `get_global_stats(self)` (line 1087)

### `memory/semantic_memory.py`

**class `MemoryEntry`** (line 40)
- `to_dict(self)` (line 48)

**class `SemanticMemory`** (line 55)
- `__init__(self)` (line 56)
- `_load(self)` (line 62)
- `_save(self)` (line 74)
- `_get_embedding(self, text)` (line 87)
- `_generate_id(self, content)` (line 113)
- `add(self, content, entry_type, metadata)` (line 117)
- `add_interaction(self, query, response, project, success)` (line 139)
- `add_code(self, code, language, description, file_path)` (line 150)
- `add_solution(self, problem, solution, tags)` (line 160)
- `add_note(self, note, category)` (line 169)
- `add_improvement_feedback(self, improvement_id, project_id, improvement_type, description, outcome, success, impact_score, lessons_learned)` (line 175)
- `add_pattern(self, pattern_name, pattern_description, examples, category)` (line 209)
- `search_similar_improvements(self, improvement_type, project_category, limit)` (line 228)
- `get_improvement_context(self, improvement_type, project_id)` (line 251)
- `get_success_rate_for_type(self, improvement_type)` (line 274)
- `get_all_improvement_stats(self)` (line 299)
- `search(self, query, limit, entry_type)` (line 344)
- `search_similar_problems(self, problem, limit)` (line 373)
- `search_relevant_code(self, description, limit)` (line 377)
- `get_context_for_query(self, query, max_entries)` (line 381)
- `stats(self)` (line 399)
- `import_from_memory_json(self, memory_file)` (line 413)
- `import_from_training_data(self, training_file)` (line 432)

### `sam_api.py`

**class `CompressionRecord`** (line 202)
- *(no methods)*

**class `CompressionMonitor`** (line 213)
- `__init__(self)` (line 226)
- `_check_daily_reset(self)` (line 235)
- `record_compression(self, original_tokens, compressed_tokens, query_type, section, budget_target)` (line 247)
- `get_stats(self)` (line 293)
- `get_summary_for_self(self)` (line 368)

**class `VisionRecord`** (line 431)
- *(no methods)*

**class `VisionStatsMonitor`** (line 443)
- `__init__(self)` (line 457)
- `_check_daily_reset(self)` (line 469)
- `record_vision_request(self, tier, processing_time_ms, task_type, escalated, success, from_cache, memory_peak_mb)` (line 484)
- `get_stats(self)` (line 542)
- `get_summary_for_self(self)` (line 617)

### `voice/voice_bridge.py`

**class `VoiceConfig`** (line 31)
- `__init__(self)` (line 32)
- `_load(self)` (line 36)
- `_save(self)` (line 48)
- `enable(self)` (line 52)
- `disable(self)` (line 57)
- `set_default_voice(self, voice_name)` (line 62)
- `add_voice(self, name, model_path, index_path)` (line 67)

**class `VoiceBridge`** (line 77)
- `__init__(self)` (line 78)
- `_check_rvc(self)` (line 82)
- `list_available_voices(self)` (line 86)
- `list_training_data(self)` (line 119)
- `text_to_speech(self, text, output_path)` (line 133)
- `convert_voice(self, audio_path, voice_name, output_path)` (line 151)
- `speak(self, text, voice_name)` (line 191)
- `play_audio(self, path)` (line 215)
- `status(self)` (line 219)

### `voice/voice_cache.py`

**class `CacheEntry`** (line 55)
- `to_dict(self)` (line 67)
- `from_dict(cls, data)` (line 81)

**class `VoiceCache`** (line 95)
- `__init__(self, cache_dir, max_size_bytes, max_age_days)` (line 164)
- `_generate_key(self, text, voice)` (line 203)
- `get(self, text, voice)` (line 233)
- `put(self, text, audio_path, voice, copy_file)` (line 277)
- `contains(self, text, voice)` (line 341)
- `remove(self, text, voice)` (line 350)
- `precompute_common(self, tts_function, voice, phrases, progress_callback)` (line 376)
- `cleanup(self, max_age_days, dry_run)` (line 435)
- `_evict_if_needed(self)` (line 495)
- `_load_metadata(self)` (line 509)
- `_save_metadata(self)` (line 534)
- `get_stats(self)` (line 549)
- `list_entries(self, limit)` (line 572)
- `clear(self)` (line 588)

### `voice/voice_extraction_pipeline.py`

**class `Segment`** (line 49)
- `duration(self)` (line 61)

**class `ExtractionMode`** (line 66)
- *(no methods)*

**class `SpeakerProfile`** (line 78)
- *(no methods)*

**class `VoiceExtractionPipeline`** (line 87)
- `__init__(self, use_gpu)` (line 100)
- `_load_diarization(self)` (line 107)
- `_load_embedding_model(self)` (line 127)
- `_load_vad(self)` (line 142)
- `detect_climax_moments(self, audio_path)` (line 153)
- `identify_target_speaker_by_climax(self, audio_files, output_dir)` (line 226)
- `extract_moaning_only(self, audio_path, output_dir, end_portion, energy_threshold, min_segment_duration, max_gap)` (line 307)
- `extract_target_moaning(self, audio_path, output_dir, target_speaker, end_portion, energy_threshold)` (line 450)
- `load_audio(self, path)` (line 592)
- `get_cache_path(self, audio_path, stage)` (line 597)
- `analyze_audio(self, audio_path)` (line 602)
- `_merge_overlapping_segments(self, segments)` (line 714)
- `extract_speaker(self, audio_path, output_path, target_speaker, min_segment_duration, min_snr_db, mode, padding_seconds)` (line 734)
- `process_directory(self, input_dir, output_dir, target_speaker, auto_select_dominant)` (line 836)

### `voice/voice_output.py`

**class `VoiceConfig`** (line 44)
- `load(cls)` (line 53)
- `save(self)` (line 59)

**class `VoiceEngine`** (line 64)
- `speak(self, text, output_path)` (line 67)

**class `MacOSVoice`** (line 71)
- `__init__(self, voice, rate)` (line 74)
- `list_voices(self)` (line 78)
- `speak(self, text, output_path)` (line 94)
- `play(self, audio_path)` (line 113)

**class `CoquiVoice`** (line 118)
- `__init__(self, model)` (line 121)
- `_get_tts(self)` (line 125)
- `speak(self, text, output_path)` (line 134)
- `play(self, audio_path)` (line 145)

**class `RVCVoice`** (line 149)
- `__init__(self, model_path, base_voice)` (line 152)
- `speak(self, text, output_path)` (line 156)
- `play(self, audio_path)` (line 173)

**class `SAMVoice`** (line 177)
- `__init__(self, config)` (line 180)
- `_create_engine(self)` (line 184)
- `speak(self, text, output_path)` (line 199)
- `list_voices(self)` (line 222)
- `set_voice(self, voice)` (line 228)
- `set_engine(self, engine)` (line 234)

### `voice/voice_pipeline.py`

**class `VoicePipelineConfig`** (line 51)
- *(no methods)*

**class `SAMVoicePipeline`** (line 80)
- `__init__(self, config, llm_generate, tts_synthesize, rvc_convert)` (line 95)
- `_setup_conversation_callbacks(self, llm_generate, tts_synthesize)` (line 151)
- `start(self)` (line 218)
- `stop(self)` (line 227)
- `process_audio(self, audio_chunk)` (line 233)
- `_update_emotion(self)` (line 276)
- `_update_stats(self, event)` (line 292)
- `get_current_emotion(self)` (line 303)
- `get_conversation_state(self)` (line 307)
- `get_stats(self)` (line 311)
- `get_emotional_trajectory(self)` (line 319)
- `set_response_strategy(self, strategy)` (line 325)
- `set_backchannel_probability(self, probability)` (line 334)
- `enable_rvc(self, enabled, model)` (line 339)
- `create_sam_integration(self)` (line 347)

### `voice/voice_preprocessor.py`

**class `URLHandling`** (line 32)
- *(no methods)*

**class `CodeBlockHandling`** (line 40)
- *(no methods)*

**class `EmojiHandling`** (line 48)
- *(no methods)*

**class `PreprocessorConfig`** (line 56)
- *(no methods)*

**class `VoicePreprocessor`** (line 359)
- `__init__(self, config)` (line 367)
- `_compile_patterns(self)` (line 384)
- `clean_text(self, text)` (line 422)
- `_handle_code_blocks(self, text)` (line 473)
- `_remove_markdown(self, text)` (line 493)
- `_handle_urls(self, text)` (line 524)
- `_handle_emojis(self, text)` (line 538)
- `_expand_abbreviations(self, text)` (line 555)
- `_expand_numbers(self, text)` (line 573)
- `_clean_quotes(self, text)` (line 624)
- `_normalize_whitespace(self, text)` (line 633)
- `split_sentences(self, text)` (line 649)
- `get_stats(self, original, cleaned)` (line 711)
- `add_abbreviation(self, abbrev, expansion)` (line 731)
- `remove_abbreviation(self, abbrev)` (line 735)

### `voice/voice_server.py`

**class `SpeakRequest`** (line 63)
- *(no methods)*

**class `VoiceInfo`** (line 71)
- *(no methods)*

**class `VoiceServer`** (line 82)
- `__init__(self)` (line 85)
- `_check_rvc(self)` (line 90)
- `_cache_key(self, text, voice, pitch, speed)` (line 100)
- `_get_cached(self, key)` (line 105)
- `_save_cache(self, key, audio)` (line 112)
- `async generate_base_tts(self, text, speed)` (line 123)
- `async convert_voice_rvc(self, input_wav, pitch_shift)` (line 167)
- `async speak(self, request)` (line 221)
- `list_voices(self)` (line 261)

### `voice/voice_settings.py`

**class `QualityLevel`** (line 51)
- *(no methods)*

**class `VoiceSettings`** (line 88)
- `__post_init__(self)` (line 148)
- `from_quality_preset(cls, quality_level)` (line 157)
- `fast(cls)` (line 180)
- `balanced(cls)` (line 185)
- `quality(cls)` (line 190)
- `apply_quality_preset(self, quality_level)` (line 194)
- `get_quality_level_enum(self)` (line 211)
- `get_quality_description(self)` (line 218)
- `add_emphasis_word(self, word)` (line 226)
- `remove_emphasis_word(self, word)` (line 231)
- `get_estimated_latency_ms(self, text_length)` (line 236)
- `to_dict(self)` (line 271)
- `from_dict(cls, data)` (line 276)
- `validate(self)` (line 283)

**class `VoiceSettingsManager`** (line 319)
- `__init__(self)` (line 333)
- `get_instance(cls)` (line 340)
- `_ensure_config_dir(self)` (line 348)
- `load(self)` (line 352)
- `save(self)` (line 373)
- `get_default(self)` (line 395)
- `reset_to_default(self)` (line 404)
- `settings(self)` (line 416)
- `update(self)` (line 422)
- `get_available_voices(self)` (line 459)

### `voice/voice_trainer.py`

**class `VoiceTrainer`** (line 32)
- `__init__(self)` (line 35)
- `get_status(self)` (line 39)
- `_get_instructions(self)` (line 53)
- `prepare_audio(self, audio_path, model_name)` (line 69)
- `start_training(self, use_docker)` (line 106)
- `stop_training(self)` (line 157)
- `_is_docker_running(self)` (line 188)
- `_is_rvc_running(self)` (line 195)

---

## 2. Top-Level Function Definitions

### `cognitive/app_knowledge_extractor.py`

- `main()` (line 1112)

### `cognitive/code_indexer.py`

- `get_code_indexer()` (line 627)

### `cognitive/code_pattern_miner.py`

- `get_miner()` (line 1311)
- `main()` (line 1327)

### `cognitive/compression.py`

- `compress_prompt(text, target_ratio)` (line 616)
- `compress_for_context(context, query, target_tokens)` (line 622)

### `cognitive/demo_full_integration.py`

- `print_header(title)` (line 24)
- `print_result(label, value, indent)` (line 32)
- `demo_text_processing(orchestrator)` (line 47)
- `demo_vision_processing(orchestrator, test_image)` (line 69)
- `demo_multi_turn(orchestrator)` (line 104)
- `demo_goals(orchestrator)` (line 127)
- `demo_emotional_state(orchestrator)` (line 153)
- `demo_learning(orchestrator)` (line 178)
- `demo_state_summary(orchestrator)` (line 196)
- `create_test_image()` (line 219)
- `run_full_demo()` (line 262)

### `cognitive/doc_indexer.py`

- `get_doc_indexer()` (line 827)

### `cognitive/emotional_model.py`

- `create_emotional_model()` (line 650)

### `cognitive/enhanced_learning.py`

- `create_learning_system()` (line 656)

### `cognitive/enhanced_memory.py`

- `create_enhanced_memory(capacity)` (line 702)

### `cognitive/enhanced_retrieval.py`

- `create_retrieval_system(db_paths)` (line 831)

### `cognitive/image_preprocessor.py`

- `get_preprocessor()` (line 601)
- `preprocess_image(path, max_size)` (line 609)
- `get_image_info(path)` (line 626)
- `estimate_memory_needed(path)` (line 639)

### `cognitive/learning_strategy.py`

- `main()` (line 566)

### `cognitive/mlx_cognitive.py`

- `_ensure_mlx()` (line 30)
- `create_mlx_engine(db_path)` (line 828)

### `cognitive/mlx_optimized.py`

- `create_optimized_engine(db_path, kv_bits, max_kv_size)` (line 396)

### `cognitive/model_evaluation.py`

- `stream_evaluate(test_data, generator, batch_size)` (line 817)
- `_get_memory_usage()` (line 900)
- `_estimate_perplexity(response)` (line 911)
- `quick_evaluate(model_generator, model_id, suite)` (line 1882)
- `compare_models(model_a_generator, model_b_generator, model_a_id, model_b_id, sample_size)` (line 1906)
- `main()` (line 1946)

### `cognitive/model_selector.py`

- `select_model(query, context_tokens, confidence_required, memory_pressure)` (line 315)

### `cognitive/multi_agent_roles.py`

- `create_coordinator(state_dir, auto_start_session)` (line 971)
- `get_role_prompt(role)` (line 993)
- `get_role_config(role)` (line 1010)
- `main()` (line 1029)

### `cognitive/personality.py`

- `get_system_prompt(mode)` (line 185)
- `get_trait_expressions(trait_name)` (line 190)
- `get_trait_avoids(trait_name)` (line 198)
- `get_random_expression(trait_name)` (line 206)
- `generate_personality_examples()` (line 212)
- `export_training_examples(output_path)` (line 294)

### `cognitive/planning_framework.py`

- `_get_available_ram_gb()` (line 101)
- `_check_mlx_available()` (line 129)
- `_check_macos()` (line 138)
- `_check_rvc_model_exists()` (line 144)
- `_check_whisper_model_exists()` (line 150)
- `_check_vlm_model_exists()` (line 157)
- `get_framework()` (line 706)
- `get_best_option(capability)` (line 714)
- `generate_plan()` (line 719)
- `main()` (line 724)

### `cognitive/quality_validator.py`

- `validate_response(response, query, confidence)` (line 391)
- `clean_response(response)` (line 401)

### `cognitive/resource_manager.py`

- `check_resources()` (line 981)
- `get_safe_max_tokens()` (line 987)
- `get_vision_status()` (line 993)
- `can_load_vision(tier)` (line 999)
- `force_unload_vision()` (line 1014)
- `get_voice_status()` (line 1021)
- `can_use_quality_voice()` (line 1027)
- `should_use_voice_fallback()` (line 1033)
- `get_recommended_voice_tier()` (line 1039)
- `can_train()` (line 1050)

### `cognitive/self_knowledge_handler.py`

- `detect_self_knowledge_query(text)` (line 71)
- `format_confidence_label(confidence)` (line 90)
- `format_time_ago(iso_timestamp)` (line 104)
- `format_self_knowledge_response(user_id, min_confidence, include_timestamps, include_confidence, personality_intro)` (line 153)
- `handle_self_knowledge_query(user_input, user_id)` (line 284)

### `cognitive/smart_vision.py`

- `analyze_image_basic(image_path)` (line 195)
- `get_dominant_color_name(rgb)` (line 238)
- `handle_color_analysis(image_path, prompt)` (line 268)
- `handle_ocr(image_path, prompt)` (line 291)
- `handle_basic_describe(image_path, prompt)` (line 321)
- `handle_face_detection(image_path, prompt)` (line 356)
- `handle_vlm(image_path, prompt, task_type)` (line 400)
- `handle_claude_escalation(image_path, prompt, task_type)` (line 465)
- `get_router()` (line 651)
- `smart_process(image_path, prompt)` (line 658)
- `quick_analyze(image_path)` (line 662)
- `get_vision_stats()` (line 666)

### `cognitive/test_cognitive_system.py`

- `main()` (line 1059)

### `cognitive/test_e2e_comprehensive.py`

- `record_result(name, passed, duration_ms, details, error)` (line 114)
- `api_client()` (line 131)
- `server_available(api_client)` (line 139)
- `generate_report()` (line 967)
- `finalize_report()` (line 1008)

### `cognitive/test_vision_system.py`

- `run_vision_tests()` (line 597)

### `cognitive/token_budget.py`

- `get_preset_budget(preset_name)` (line 286)

### `cognitive/ui_awareness.py`

- `check_accessibility_permissions()` (line 140)
- `get_ax_value(element, attribute)` (line 147)
- `get_ax_actions(element)` (line 160)
- `find_app_pid(app_name)` (line 173)
- `find_all_apps()` (line 201)
- `extract_element(element, depth, max_depth)` (line 225)
- `extract_all_text(element, depth, max_depth)` (line 272)
- `find_elements_by_role(element, role_filter, depth, max_depth)` (line 297)
- `find_elements_by_text(element, text_filter, depth, max_depth)` (line 316)
- `detect_state(all_text)` (line 343)
- `main()` (line 756)

### `cognitive/unified_orchestrator.py`

- `detect_image_followup(query, has_image_context)` (line 193)
- `create_cognitive_orchestrator(db_path, retrieval_paths)` (line 1738)

### `cognitive/vision_client.py`

- `process_image(image, prompt, use_http, base_url)` (line 654)
- `extract_text(image, use_http, base_url)` (line 684)
- `smart_analyze(image, prompt, use_http, base_url)` (line 716)

### `cognitive/vision_engine.py`

- `_ensure_mlx_vlm()` (line 212)
- `measure_memory_usage()` (line 1316)
- `_get_memory_recommendations(available_gb, can_run_vlm)` (line 1456)
- `create_vision_engine(adapter_path, max_memory_mb)` (line 1485)
- `describe_image(image_path, detail_level)` (line 1496)
- `detect_objects(image_path, target)` (line 1529)
- `answer_about_image(image_path, question)` (line 1552)

### `cognitive/vision_selector.py`

- `get_selector()` (line 737)
- `select_tier(task, available_ram)` (line 745)
- `get_recommended_tier(image_path, prompt)` (line 778)

### `execution/auto_fix.py`

- `detect_issues(path)` (line 1555)
- `fix_file(path, create_backups)` (line 1574)
- `fix_project(path, create_backups)` (line 1588)
- `get_stats()` (line 1602)

### `execution/auto_fix_control.py`

- `get_db_path()` (line 64)
- `get_auto_fix_controller()` (line 1370)
- `notify_auto_fixes_available(project_id, issues)` (line 1380)
- `notify_auto_fixes_completed(project_id, results)` (line 1412)
- `notify_auto_fix_failed(project_id, issue, error)` (line 1446)
- `api_autofix_permissions_get(project_id)` (line 1474)
- `api_autofix_permissions_update(project_id, config)` (line 1500)
- `api_autofix_stats(project_id)` (line 1540)
- `api_autofix_run(project_id, dry_run)` (line 1568)
- `api_autofix_pending(project_id, limit)` (line 1622)
- `api_autofix_history(file_path, limit)` (line 1650)
- `main()` (line 1684)

### `execution/command_classifier.py`

- `classify_command(command)` (line 924)
- `is_safe_command(command)` (line 938)
- `get_command_dangers(command)` (line 952)
- `main()` (line 970)
- `_run_tests()` (line 1028)

### `execution/command_proposer.py`

- `propose_fix(problem, context)` (line 1238)
- `propose_task(task, project_context)` (line 1253)
- `format_proposal(proposal, format_type)` (line 1268)

### `execution/escalation_handler.py`

- `_init_cognitive()` (line 29)
- `get_cognitive()` (line 138)
- `evaluate_confidence(response, original_prompt)` (line 142)
- `should_auto_escalate(confidence, complexity, reason)` (line 195)
- `escalate_to_claude(prompt, context)` (line 215)
- `process_request(prompt, auto_escalate, force_claude)` (line 289)
- `interactive_mode()` (line 393)

### `execution/escalation_learner.py`

- `main()` (line 531)

### `execution/execution_history.py`

- `get_rollback_manager()` (line 1252)
- `get_execution_logger()` (line 1260)
- `api_execution_history(limit, project_id)` (line 1268)
- `api_execution_stats()` (line 1299)
- `api_execution_rollback(checkpoint_id)` (line 1321)
- `api_execution_checkpoints(project_id, limit)` (line 1346)
- `api_checkpoint_details(checkpoint_id)` (line 1374)
- `api_create_checkpoint(project_id, description)` (line 1405)
- `api_cleanup_checkpoints(days)` (line 1434)
- `api_export_executions(start_date, end_date)` (line 1460)
- `main()` (line 1494)

### `execution/safe_executor.py`

- `check_with_classifier(command)` (line 935)
- `create_safe_context(project_id, working_directory, dry_run)` (line 965)
- `get_executor()` (line 996)
- `safe_execute(command, working_dir, timeout, dry_run)` (line 1008)

### `memory/context_budget.py`

- `get_importance_scorer()` (line 1858)
- `get_adaptive_context_manager()` (line 2419)

### `memory/conversation_memory.py`

- `init_database(db_path)` (line 85)
- `main()` (line 672)

### `memory/fact_memory.py`

- `get_fact_db_path()` (line 130)
- `is_external_drive_mounted()` (line 139)
- `generate_fact_id(user_id, fact, category)` (line 371)
- `generate_history_id(fact_id, timestamp)` (line 377)
- `decay_confidence_ebbinghaus(initial, days_elapsed, decay_rate, reinforcement_count, floor)` (line 383)
- `decay_confidence(initial, days_elapsed, decay_rate, reinforcement_count, floor)` (line 457)
- `get_fact_db()` (line 1927)
- `build_user_context(user_id, min_confidence, max_tokens)` (line 1939)
- `build_context_with_project(user_id, project_id, min_confidence, max_tokens)` (line 2026)
- `get_fact_memory()` (line 2142)
- `get_user_context(user_id, max_tokens)` (line 2147)
- `remember_fact(user_id, fact, category)` (line 2172)
- `main()` (line 2202)

### `memory/infinite_context.py`

- `main()` (line 1039)

### `memory/project_context.py`

- `get_current_project(path)` (line 461)
- `get_session_recall()` (line 1020)
- `get_profile_loader()` (line 1554)
- `get_project_watcher(poll_interval, auto_start)` (line 1866)
- `get_session_state()` (line 2463)
- `get_project_context()` (line 2879)

### `memory/rag_feedback.py`

- `get_rag_feedback_db_path()` (line 71)
- `get_rag_feedback_tracker()` (line 1138)
- `record_rag_feedback(query, sources, used_source_ids, rating, project_id, response_id)` (line 1146)
- `get_source_quality_scores(project_id, min_confidence, limit)` (line 1160)
- `adjust_relevance_score(source_id, base_score, project_id, query)` (line 1171)

### `memory/semantic_memory.py`

- `get_memory()` (line 455)
- `search(query, limit)` (line 463)
- `add_interaction(query, response, project)` (line 468)
- `get_context(query)` (line 473)
- `add_improvement_feedback(improvement_id, project_id, improvement_type, description, outcome, success, impact_score, lessons_learned)` (line 480)
- `get_improvement_context(improvement_type, project_id)` (line 497)
- `get_improvement_stats()` (line 502)

### `orchestrator.py`

- `get_active_model()` (line 128)
- `warm_models()` (line 151)
- `route_request(message)` (line 168)
- `handle_re(message)` (line 207)
- `handle_voice(message)` (line 231)
- `_mlx_generate(prompt, max_tokens, temperature)` (line 278)
- `handle_chat(message)` (line 296)
- `handle_roleplay(message)` (line 302)
- `handle_code(message)` (line 313)
- `handle_image(message)` (line 350)
- `handle_reason(message)` (line 425)
- `handle_improve(message)` (line 497)
- `handle_project(message)` (line 749)
- `handle_data(message)` (line 861)
- `handle_terminal(message)` (line 1100)
- `estimate_tokens(text)` (line 1258)
- `track_impact(message, response, source, route)` (line 1263)
- `orchestrate(message, privacy_level)` (line 1280)

### `sam_api.py`

- `get_feedback_db()` (line 79)
- `get_distillation_db()` (line 94)
- `get_distillation_stats()` (line 110)
- `get_sam_intelligence()` (line 186)
- `get_compression_monitor()` (line 398)
- `record_compression_stats(original_tokens, compressed_tokens, query_type, section, budget_target)` (line 406)
- `get_vision_stats_monitor()` (line 653)
- `record_vision_stats(tier, processing_time_ms, task_type, escalated, success, from_cache, memory_peak_mb)` (line 661)
- `load_inventory()` (line 687)
- `api_query(query, speak)` (line 704)
- `api_projects()` (line 747)
- `api_memory()` (line 782)
- `api_status()` (line 792)
- `api_search(query)` (line 833)
- `api_categories()` (line 866)
- `api_starred()` (line 912)
- `api_speak(text, voice)` (line 938)
- `api_voices()` (line 962)
- `get_training_stats()` (line 984)
- `api_self()` (line 1066)
- `api_suggest(limit)` (line 1130)
- `api_proactive()` (line 1149)
- `api_learning()` (line 1167)
- `api_feedback(improvement_id, success, impact, lessons)` (line 1208)
- `api_scan()` (line 1227)
- `api_think(query)` (line 1255)
- `api_orchestrate(message, auto_escalate)` (line 1277)
- `get_cognitive_orchestrator()` (line 1336)
- `api_cognitive_process(query, user_id)` (line 1352)
- `api_cognitive_state()` (line 1381)
- `api_cognitive_mood()` (line 1398)
- `api_resources()` (line 1415)
- `api_context_stats()` (line 1455)
- `_update_activity()` (line 1511)
- `_get_idle_seconds()` (line 1516)
- `_start_idle_watcher()` (line 1523)
- `api_unload_model()` (line 1555)
- `api_cognitive_feedback(response_id, helpful, comment, query, response, user_id, session_id, feedback_type, rating, correction, correction_type, what_was_wrong, preferred_response, comparison_basis, flag_type, flag_details, domain, response_confidence, escalated_to_claude, response_timestamp, conversation_context)` (line 1589)
- `api_cognitive_feedback_stats()` (line 1735)
- `api_cognitive_feedback_recent(limit, domain, feedback_type, session_id)` (line 1761)
- `api_notifications()` (line 1800)
- `api_feedback_dashboard()` (line 1838)
- `api_intelligence_stats()` (line 1871)
- `api_user_facts(user_id)` (line 1887)
- `api_remember_fact(user_id, fact, category)` (line 1906)
- `api_fact_context(user_id)` (line 1931)
- `api_facts_list(user_id, category, min_confidence, limit)` (line 1967)
- `api_facts_add(fact, category, user_id, source, confidence)` (line 2018)
- `api_facts_remove(fact_id)` (line 2058)
- `api_facts_search(query, user_id, limit)` (line 2095)
- `api_facts_get(fact_id)` (line 2140)
- `api_project_context(path)` (line 2189)
- `api_save_session(project_path, working_on, notes)` (line 2227)
- `api_recent_projects(limit)` (line 2255)
- `api_project_current()` (line 2283)
- `api_project_todos(path, limit)` (line 2370)
- `api_code_index(path, project_id, force)` (line 2399)
- `api_code_search(query, project_id, entity_type, limit)` (line 2418)
- `api_code_stats(project_id)` (line 2448)
- `api_index_status()` (line 2472)
- `api_index_build(project_path, project_id, force)` (line 2541)
- `api_index_clear(project_id)` (line 2589)
- `api_index_watch(project_path, project_id)` (line 2642)
- `api_index_watch_stop()` (line 2809)
- `api_cognitive_escalate(query)` (line 2840)
- `api_cognitive_stream(query, user_id)` (line 2856)
- `api_think_stream(query, mode)` (line 2903)
- `api_think_colors()` (line 2945)
- `get_vision_engine()` (line 2963)
- `api_vision_process(image_path, prompt, model, image_base64)` (line 2976)
- `api_vision_stream(image_base64, image_path, prompt)` (line 3055)
- `api_vision_analyze(image_base64, image_path, prompt)` (line 3197)
- `api_vision_describe(image_path, detail_level)` (line 3277)
- `api_vision_ocr(image_path, image_base64)` (line 3315)
- `api_vision_detect(image_path, target)` (line 3425)
- `api_vision_models()` (line 3448)
- `api_vision_stats()` (line 3471)
- `get_smart_vision_router()` (line 3520)
- `api_vision_smart(image_path, image_base64, prompt, force_tier, skip_cache)` (line 3533)
- `api_vision_smart_stats()` (line 3634)
- `api_image_context_get()` (line 3653)
- `api_image_context_clear()` (line 3690)
- `api_image_chat(query, image_path, image_base64, user_id)` (line 3707)
- `api_image_followup_check(query)` (line 3802)
- `get_voice_pipeline()` (line 3833)
- `api_voice_start()` (line 3846)
- `api_voice_stop()` (line 3869)
- `api_voice_status()` (line 3886)
- `api_voice_emotion()` (line 3924)
- `api_voice_config(config_updates)` (line 3964)
- `api_voice_process_audio(audio_base64)` (line 4006)
- `api_voice_process_stream(audio_base64)` (line 4071)
- `api_voice_conversation_state()` (line 4123)
- `api_distillation_review_pending(limit, domain)` (line 4169)
- `api_distillation_review_details(example_id)` (line 4215)
- `api_distillation_review_action(example_id, action, notes)` (line 4242)
- `api_distillation_review_batch(action, threshold)` (line 4285)
- `api_distillation_review_stats()` (line 4332)
- `run_server(port)` (line 4353)
- `main()` (line 5299)

### `voice/voice_bridge.py`

- `get_bridge()` (line 236)
- `speak(text, voice)` (line 244)
- `list_voices()` (line 249)

### `voice/voice_cache.py`

- `get_cache()` (line 610)
- `main()` (line 619)

### `voice/voice_extraction_pipeline.py`

- `main()` (line 951)

### `voice/voice_output.py`

- `main()` (line 242)

### `voice/voice_pipeline.py`

- `create_voice_pipeline(llm_fn, tts_fn, rvc_fn)` (line 362)

### `voice/voice_preprocessor.py`

- `number_to_words(n)` (line 183)
- `float_to_words(f, decimal_places)` (line 229)
- `clean_for_tts(text)` (line 742)
- `split_for_tts(text, clean)` (line 758)

### `voice/voice_server.py`

- `async root()` (line 305)
- `async startup()` (line 313)
- `async health()` (line 319)
- `async list_voices()` (line 328)
- `async speak(request)` (line 335)
- `async speak_stream(request)` (line 362)
- `main()` (line 371)

### `voice/voice_settings.py`

- `get_voice_settings()` (line 519)
- `save_voice_settings()` (line 524)
- `update_voice_settings()` (line 529)
- `reset_voice_settings()` (line 534)
- `get_available_voices()` (line 539)
- `api_get_voice_settings()` (line 546)
- `api_update_voice_settings(updates)` (line 572)
- `main()` (line 588)

### `voice/voice_trainer.py`

- `get_trainer()` (line 207)
- `voice_status()` (line 215)
- `voice_prepare(audio_path, model_name)` (line 219)
- `voice_start()` (line 223)
- `voice_stop()` (line 227)

---

## 3. Functions NEVER Called Anywhere in Codebase

**Total uncalled top-level functions:** 8

| File | Function | Line |
|------|----------|------|
| `cognitive/demo_full_integration.py` | `print_result` | 32 |
| `cognitive/smart_vision.py` | `quick_analyze` | 662 |
| `cognitive/test_e2e_comprehensive.py` | `finalize_report` | 1008 |
| `cognitive/ui_awareness.py` | `extract_element` | 225 |
| `memory/context_budget.py` | `get_adaptive_context_manager` | 2419 |
| `memory/semantic_memory.py` | `get_improvement_stats` | 502 |
| `sam_api.py` | `api_user_facts` | 1887 |
| `voice/voice_server.py` | `speak_stream` | 362 |

---

## 4. Classes NEVER Instantiated/Referenced Anywhere

**Total unreferenced classes:** 11

| File | Class | Line |
|------|-------|------|
| `cognitive/mlx_cognitive.py` | `ModelSize` | 44 |
| `cognitive/model_evaluation.py` | `ModelGenerator` | 190 |
| `cognitive/test_e2e_comprehensive.py` | `TestAPIContracts` | 154 |
| `cognitive/test_e2e_comprehensive.py` | `TestChaos` | 749 |
| `cognitive/test_e2e_comprehensive.py` | `TestLoad` | 677 |
| `cognitive/test_e2e_comprehensive.py` | `TestPerformance` | 857 |
| `cognitive/test_e2e_comprehensive.py` | `TestPersonality` | 592 |
| `cognitive/test_e2e_comprehensive.py` | `TestRegression` | 921 |
| `cognitive/test_e2e_comprehensive.py` | `TestResourceManagement` | 521 |
| `cognitive/test_e2e_comprehensive.py` | `TestStreaming` | 411 |
| `cognitive/ui_awareness.py` | `SAMUIAwareness` | 630 |

---

## 5. Duplicate Function/Class Names Across Files

### Duplicate Function Names

**`list_voices`** -- defined in 2 files:
- `voice/voice_bridge.py` (line 249)
- `voice/voice_server.py` (line 328)

**`main`** -- defined in 21 files:
- `sam_api.py` (line 5299)
- `cognitive/app_knowledge_extractor.py` (line 1112)
- `cognitive/code_pattern_miner.py` (line 1327)
- `cognitive/learning_strategy.py` (line 566)
- `cognitive/model_evaluation.py` (line 1946)
- `cognitive/multi_agent_roles.py` (line 1029)
- `cognitive/planning_framework.py` (line 724)
- `cognitive/test_cognitive_system.py` (line 1059)
- `cognitive/ui_awareness.py` (line 756)
- `memory/conversation_memory.py` (line 672)
- `memory/fact_memory.py` (line 2202)
- `memory/infinite_context.py` (line 1039)
- `voice/voice_cache.py` (line 619)
- `voice/voice_extraction_pipeline.py` (line 951)
- `voice/voice_output.py` (line 242)
- `voice/voice_server.py` (line 371)
- `voice/voice_settings.py` (line 588)
- `execution/auto_fix_control.py` (line 1684)
- `execution/command_classifier.py` (line 970)
- `execution/escalation_learner.py` (line 531)
- `execution/execution_history.py` (line 1494)

**`speak`** -- defined in 2 files:
- `voice/voice_bridge.py` (line 244)
- `voice/voice_server.py` (line 335)

### Duplicate Class Names

**`AutoFixableIssue`** -- defined in 2 files:
- `execution/auto_fix.py` (line 54)
- `execution/auto_fix_control.py` (line 75)

**`CacheEntry`** -- defined in 2 files:
- `cognitive/enhanced_learning.py` (line 255)
- `voice/voice_cache.py` (line 55)

**`DetectedIssue`** -- defined in 2 files:
- `execution/auto_fix.py` (line 95)
- `execution/auto_fix_control.py` (line 132)

**`EscalationReason`** -- defined in 2 files:
- `cognitive/quality_validator.py` (line 29)
- `execution/escalation_handler.py` (line 74)

**`ExecutionResult`** -- defined in 3 files:
- `execution/command_proposer.py` (line 220)
- `execution/execution_history.py` (line 74)
- `execution/safe_executor.py` (line 166)

**`ExecutionStatus`** -- defined in 2 files:
- `execution/execution_history.py` (line 65)
- `execution/safe_executor.py` (line 156)

**`FixResult`** -- defined in 2 files:
- `execution/auto_fix.py` (line 142)
- `execution/auto_fix_control.py` (line 172)

**`QueryType`** -- defined in 2 files:
- `cognitive/compression.py` (line 418)
- `memory/context_budget.py` (line 70)

**`TaskType`** -- defined in 2 files:
- `cognitive/model_selector.py` (line 17)
- `cognitive/smart_vision.py` (line 46)

**`TestResult`** -- defined in 3 files:
- `cognitive/test_cognitive_system.py` (line 30)
- `cognitive/test_e2e_comprehensive.py` (line 50)
- `cognitive/test_vision_system.py` (line 29)

**`UIElement`** -- defined in 2 files:
- `cognitive/app_knowledge_extractor.py` (line 130)
- `cognitive/ui_awareness.py` (line 86)

**`VisionResponse`** -- defined in 2 files:
- `cognitive/unified_orchestrator.py` (line 333)
- `cognitive/vision_client.py` (line 56)

**`VisionResult`** -- defined in 2 files:
- `cognitive/smart_vision.py` (line 91)
- `cognitive/vision_engine.py` (line 172)

**`VisionTier`** -- defined in 4 files:
- `cognitive/resource_manager.py` (line 43)
- `cognitive/smart_vision.py` (line 39)
- `cognitive/vision_client.py` (line 47)
- `cognitive/vision_selector.py` (line 101)

**`VoiceConfig`** -- defined in 2 files:
- `voice/voice_bridge.py` (line 31)
- `voice/voice_output.py` (line 44)
