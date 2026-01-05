// Intelligence Engine V2 - Comprehensive Coverage
//
// Goal: Handle ANY reasonable request without AI
// Strategy: Massive keyword database + smart entity extraction + compound workflows

use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::process::Command;
use regex::Regex;

// =============================================================================
// COMPREHENSIVE TASK TAXONOMY
// =============================================================================

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum TaskType {
    // FILE OPERATIONS
    FindFiles,
    ReadFile,
    WriteFile,
    EditFile,
    DeleteFile,
    MoveFile,
    CopyFile,
    RenameFile,
    CreateFile,
    CreateDirectory,
    ListDirectory,
    TreeView,
    FileInfo,
    FileSize,
    FindLargeFiles,
    FindRecentFiles,
    FindDuplicates,
    CompareFiles,
    MergeFiles,
    SplitFile,
    CompressFile,
    ExtractArchive,

    // CODE SEARCH
    SearchText,
    SearchRegex,
    SearchFunction,
    SearchClass,
    SearchMethod,
    SearchVariable,
    SearchImport,
    SearchExport,
    SearchType,
    SearchInterface,
    SearchEnum,
    SearchConstant,
    SearchComment,
    SearchTodo,
    SearchFixme,
    SearchBug,
    SearchError,
    SearchDeprecated,
    FindReferences,
    FindDefinition,
    FindImplementation,
    FindUsages,
    SearchAndReplace,

    // CODE ANALYSIS
    ListFunctions,
    ListClasses,
    ListMethods,
    ListVariables,
    ListImports,
    ListExports,
    ListTypes,
    ListInterfaces,
    ListEnums,
    ListConstants,
    ShowOutline,
    ShowStructure,
    ShowDependencies,
    ShowCallGraph,
    CountLines,
    CountFunctions,
    CountClasses,
    AnalyzeComplexity,
    FindDeadCode,
    FindUnusedImports,
    FindUnusedVariables,

    // CODE QUALITY
    Lint,
    Format,
    TypeCheck,
    CheckSyntax,
    CheckStyle,
    FindBugs,
    SecurityScan,
    PerformanceCheck,
    AccessibilityCheck,

    // CODE GENERATION
    GenerateFunction,
    GenerateClass,
    GenerateInterface,
    GenerateType,
    GenerateTest,
    GenerateTestSuite,
    GenerateMock,
    GenerateFixture,
    GenerateDocstring,
    GenerateComment,
    GenerateReadme,
    GenerateChangelog,
    GenerateLicense,
    GenerateGitignore,
    GenerateDockerfile,
    GenerateMakefile,
    GenerateConfig,
    ScaffoldProject,
    ScaffoldComponent,
    ScaffoldModule,

    // REFACTORING
    RenameSymbol,
    ExtractFunction,
    ExtractVariable,
    ExtractConstant,
    ExtractInterface,
    InlineFunction,
    InlineVariable,
    MoveToFile,
    SplitFunction,
    MergeFunctions,
    ConvertToAsync,
    ConvertToSync,
    AddParameter,
    RemoveParameter,
    ChangeSignature,
    SimplifyCode,
    OptimizeImports,

    // GIT OPERATIONS
    GitStatus,
    GitDiff,
    GitDiffStaged,
    GitDiffFile,
    GitLog,
    GitLogFile,
    GitLogOneline,
    GitBlame,
    GitShow,
    GitBranch,
    GitBranchList,
    GitBranchCreate,
    GitBranchDelete,
    GitBranchRename,
    GitCheckout,
    GitCheckoutFile,
    GitSwitch,
    GitMerge,
    GitRebase,
    GitCherryPick,
    GitStash,
    GitStashList,
    GitStashPop,
    GitStashDrop,
    GitAdd,
    GitAddAll,
    GitAddFile,
    GitReset,
    GitResetFile,
    GitResetHard,
    GitRevert,
    GitCommit,
    GitCommitAmend,
    GitPush,
    GitPushForce,
    GitPull,
    GitFetch,
    GitClone,
    GitInit,
    GitRemote,
    GitTag,
    GitTagCreate,
    GitTagDelete,
    GitClean,
    GitGc,

    // BUILD & RUN
    Build,
    BuildRelease,
    BuildDebug,
    Clean,
    Rebuild,
    Run,
    RunDebug,
    RunRelease,
    Watch,
    Dev,
    Start,
    Stop,
    Restart,

    // TESTING
    Test,
    TestAll,
    TestFile,
    TestFunction,
    TestWatch,
    TestCoverage,
    TestSnapshot,
    TestUpdate,
    Benchmark,

    // DEPENDENCIES
    Install,
    InstallDev,
    Uninstall,
    Update,
    UpdateAll,
    Outdated,
    Audit,
    AuditFix,
    Lock,

    // PROCESSES
    ProcessList,
    ProcessFind,
    ProcessKill,
    ProcessKillByName,
    ProcessKillByPort,
    PortList,
    PortFind,
    PortKill,

    // SYSTEM
    SystemInfo,
    DiskUsage,
    DiskFree,
    MemoryUsage,
    CpuUsage,
    NetworkInfo,
    EnvList,
    EnvGet,
    EnvSet,
    PathList,
    WhichCommand,

    // DOCKER
    DockerPs,
    DockerImages,
    DockerBuild,
    DockerRun,
    DockerStop,
    DockerRm,
    DockerLogs,
    DockerExec,
    DockerCompose,
    DockerPrune,

    // DATABASE
    DbConnect,
    DbQuery,
    DbList,
    DbCreate,
    DbDrop,
    DbMigrate,
    DbSeed,
    DbBackup,
    DbRestore,

    // HTTP/API
    HttpGet,
    HttpPost,
    HttpPut,
    HttpDelete,
    ApiTest,
    CurlRequest,
    HttpHead,
    HttpOptions,
    HttpPatch,

    // PACKAGE MANAGERS (expanded)
    YarnInstall,
    YarnAdd,
    YarnRemove,
    YarnUpgrade,
    YarnDev,
    YarnBuild,
    YarnStart,
    PnpmInstall,
    PnpmAdd,
    PnpmRemove,
    PoetryInstall,
    PoetryAdd,
    PoetryRemove,
    PoetryUpdate,
    PipenvInstall,
    PipenvLock,
    BunInstall,
    BunAdd,
    BunRun,

    // CLOUD/DEVOPS
    AwsCli,
    AwsS3Ls,
    AwsS3Cp,
    AwsS3Sync,
    AwsEc2List,
    AwsLambdaList,
    AwsLambdaInvoke,
    GcloudList,
    GcloudDeploy,
    AzureCli,
    KubectlGet,
    KubectlDescribe,
    KubectlLogs,
    KubectlApply,
    KubectlDelete,
    KubectlExec,
    KubectlPortForward,
    HelmInstall,
    HelmUpgrade,
    HelmList,
    HelmUninstall,
    TerraformInit,
    TerraformPlan,
    TerraformApply,
    TerraformDestroy,
    AnsiblePlaybook,
    AnsibleInventory,

    // ADVANCED GIT
    GitBisect,
    GitBisectStart,
    GitBisectGood,
    GitBisectBad,
    GitBisectReset,
    GitWorktree,
    GitWorktreeAdd,
    GitWorktreeList,
    GitReflog,
    GitFsck,
    GitSubmodule,
    GitSubmoduleUpdate,
    GitLfs,
    GitLfsPull,
    GitLfsPush,
    GitArchive,
    GitBundle,
    GitShortlog,
    GitDescribe,
    GitNotes,

    // DEBUGGING/PROFILING
    LldbRun,
    LldbAttach,
    GdbRun,
    GdbAttach,
    Valgrind,
    Strace,
    Dtrace,
    PerfRecord,
    PerfReport,
    Flamegraph,
    HeapProfile,
    CpuProfile,
    MemoryProfile,

    // SECURITY SCANNING
    TrivyScan,
    SnykTest,
    BanditScan,
    SafetyCheck,
    NpmAuditFix,
    CargoAuditFix,
    OsvScanner,
    GitleaksScan,
    SemgrepScan,

    // DOCUMENTATION
    Rustdoc,
    Jsdoc,
    Typedoc,
    Sphinx,
    Mkdocs,
    Docusaurus,
    Storybook,

    // DATABASE CLI
    PsqlConnect,
    PsqlQuery,
    PsqlList,
    MysqlConnect,
    MysqlQuery,
    MysqlList,
    SqliteQuery,
    SqliteList,
    RedisConnect,
    RedisCli,
    RedisGet,
    RedisSet,
    RedisKeys,
    MongoConnect,
    MongoshQuery,
    MongoList,

    // TMUX/SCREEN
    TmuxNew,
    TmuxList,
    TmuxAttach,
    TmuxKill,
    TmuxSplit,
    TmuxSend,
    ScreenNew,
    ScreenList,
    ScreenAttach,

    // SSH/REMOTE
    SshConnect,
    SshCopy,
    SshTunnel,
    ScpCopy,
    RsyncSync,
    SftpConnect,

    // LOG ANALYSIS
    TailFollow,
    TailLines,
    Journalctl,
    JournalctlFollow,
    LogGrep,
    LogParse,
    AwsLogs,

    // FRAMEWORK SPECIFIC
    DjangoManage,
    DjangoMigrate,
    DjangoShell,
    DjangoTest,
    RailsConsole,
    RailsServer,
    RailsMigrate,
    RailsGenerate,
    NextDev,
    NextBuild,
    NextStart,
    NuxtDev,
    NuxtBuild,
    ViteDev,
    ViteBuild,
    CreateReactApp,
    AngularServe,
    AngularBuild,
    FlutterRun,
    FlutterBuild,
    ExpoStart,
    ReactNativeStart,

    // COMPOUND COMMANDS
    CommitAndPush,
    BuildAndTest,
    BuildAndRun,
    PullAndBuild,
    CleanAndBuild,
    TestAndCoverage,
    LintAndFix,
    FormatAndCommit,

    // CONTEXT-AWARE
    RunAgain,
    Undo,
    Retry,
    LastCommand,
    EditLastFile,
    CdBack,
    CdPrevious,

    // MISC
    Help,
    Version,
    Clear,
    History,
    Alias,
    Time,
    Date,
    Calendar,
    Calculator,
    Uuid,
    Base64Encode,
    Base64Decode,
    Md5Sum,
    Sha256Sum,
    JsonFormat,
    JsonValidate,
    XmlFormat,
    YamlToJson,
    JsonToYaml,
    UrlEncode,
    UrlDecode,
    Hostname,
    Whoami,
    Uptime,

    // NETWORK
    Ping,
    Traceroute,
    Dig,
    Nslookup,
    Netstat,
    Ss,
    Ifconfig,
    IpAddr,
    Arp,
    Nmap,
    Tcpdump,

    // MEDIA/FILES
    ImageInfo,
    ImageResize,
    ImageConvert,
    VideoInfo,
    AudioInfo,
    PdfInfo,
    PdfMerge,
    PdfSplit,

    // CATCH-ALL
    Shell,
    Unknown,
}

// =============================================================================
// MASSIVE KEYWORD DATABASE
// =============================================================================

pub struct KeywordDatabase {
    patterns: HashMap<TaskType, Vec<&'static str>>,
    // Priority patterns - if these match, use this task type immediately
    exact_matches: HashMap<&'static str, TaskType>,
    // Negative patterns - if these are present, DON'T use this task type
    exclusions: HashMap<TaskType, Vec<&'static str>>,
}

impl KeywordDatabase {
    pub fn new() -> Self {
        let mut patterns: HashMap<TaskType, Vec<&'static str>> = HashMap::new();
        let mut exact_matches: HashMap<&'static str, TaskType> = HashMap::new();
        let mut exclusions: HashMap<TaskType, Vec<&'static str>> = HashMap::new();

        // ===================
        // FILE OPERATIONS
        // ===================
        patterns.insert(TaskType::FindFiles, vec![
            "find", "find all", "find files", "search for files", "locate", "locate files",
            "where is", "where are", "look for", "get all", "list all", "show all",
            "files matching", "files named", "files with extension", "files ending in",
            "*.py", "*.rs", "*.js", "*.ts", "*.go", "*.java", "*.c", "*.cpp", "*.h",
            "*.md", "*.txt", "*.json", "*.yaml", "*.yml", "*.toml", "*.xml", "*.html",
            "*.css", "*.scss", "*.vue", "*.jsx", "*.tsx", "*.rb", "*.php", "*.sh",
        ]);
        exclusions.insert(TaskType::FindFiles, vec!["function", "class", "def ", "fn "]);

        patterns.insert(TaskType::ReadFile, vec![
            "read", "read file", "show file", "cat", "display", "print", "view",
            "open", "contents of", "content of", "what's in", "show me", "see",
            "look at", "examine", "inspect", "output", "dump",
        ]);

        patterns.insert(TaskType::WriteFile, vec![
            "write", "write to", "write file", "save", "save to", "save as",
            "create file", "output to", "store", "put in", "dump to",
        ]);

        patterns.insert(TaskType::EditFile, vec![
            "edit", "modify", "change", "update", "alter", "fix in", "correct",
            "replace in", "add to", "remove from", "insert", "delete from",
        ]);

        patterns.insert(TaskType::DeleteFile, vec![
            "delete", "remove", "rm", "del", "erase", "destroy", "trash",
        ]);
        exclusions.insert(TaskType::DeleteFile, vec!["git", "branch"]);

        patterns.insert(TaskType::MoveFile, vec![
            "move", "mv", "relocate", "transfer",
        ]);

        patterns.insert(TaskType::CopyFile, vec![
            "copy", "cp", "duplicate", "clone file",
        ]);
        exclusions.insert(TaskType::CopyFile, vec!["git"]);

        patterns.insert(TaskType::CreateDirectory, vec![
            "mkdir", "create directory", "create folder", "make directory", "make folder",
            "new directory", "new folder", "add directory", "add folder",
        ]);

        patterns.insert(TaskType::ListDirectory, vec![
            "ls", "list", "dir", "directory", "folder", "what's in", "show folder",
            "contents of folder", "files in", "list files",
        ]);
        exclusions.insert(TaskType::ListDirectory, vec!["function", "class", "method"]);

        patterns.insert(TaskType::TreeView, vec![
            "tree", "directory tree", "folder structure", "project structure",
            "file tree", "show tree", "hierarchy",
        ]);

        patterns.insert(TaskType::FileInfo, vec![
            "file info", "file details", "file stat", "stat", "file size",
            "when was", "modified", "created", "permissions",
        ]);

        patterns.insert(TaskType::FindLargeFiles, vec![
            "large files", "big files", "biggest files", "largest files",
            "files over", "files larger than", "space hogs",
        ]);

        patterns.insert(TaskType::FindRecentFiles, vec![
            "recent files", "recently modified", "recently changed", "newest files",
            "latest files", "files from today", "files from yesterday",
        ]);

        patterns.insert(TaskType::ExtractArchive, vec![
            "extract", "unzip", "untar", "unrar", "decompress", "expand",
            "unpack", "open archive",
        ]);

        patterns.insert(TaskType::CompressFile, vec![
            "compress", "zip", "tar", "gzip", "archive", "pack",
        ]);

        // ===================
        // CODE SEARCH
        // ===================
        patterns.insert(TaskType::SearchText, vec![
            "search", "search for", "grep", "find text", "look for", "contains",
            "where does", "which files contain", "files with", "occurrences of",
            "instances of", "mentions of",
        ]);
        exclusions.insert(TaskType::SearchText, vec![
            "function", "class", "def ", "fn ", "method", "variable",
        ]);

        patterns.insert(TaskType::SearchRegex, vec![
            "regex", "regular expression", "pattern match", "search pattern",
            "match pattern",
        ]);

        patterns.insert(TaskType::SearchFunction, vec![
            "find function", "search function", "where is function", "function named",
            "function called", "def ", "fn ", "func ", "function ", "method named",
            "find method", "search method", "where is method",
        ]);

        patterns.insert(TaskType::SearchClass, vec![
            "find class", "search class", "where is class", "class named",
            "class called", "struct ", "type ", "interface ",
        ]);

        patterns.insert(TaskType::SearchVariable, vec![
            "find variable", "search variable", "where is variable", "variable named",
            "const ", "let ", "var ",
        ]);

        patterns.insert(TaskType::SearchImport, vec![
            "find import", "search import", "where is imported", "import ",
            "require", "from ", "use ", "include",
        ]);

        patterns.insert(TaskType::SearchTodo, vec![
            "find todo", "search todo", "todos", "todo list", "todo:", "TODO",
        ]);

        patterns.insert(TaskType::SearchFixme, vec![
            "find fixme", "search fixme", "fixmes", "fixme:", "FIXME",
        ]);

        patterns.insert(TaskType::SearchError, vec![
            "find error", "search error", "errors", "find bug", "search bug", "bugs",
            "issues", "problems",
        ]);

        patterns.insert(TaskType::FindReferences, vec![
            "find references", "references to", "usages of", "where is used",
            "who uses", "what uses", "callers of",
        ]);

        patterns.insert(TaskType::FindDefinition, vec![
            "find definition", "go to definition", "where is defined", "definition of",
            "where does come from",
        ]);

        patterns.insert(TaskType::SearchAndReplace, vec![
            "replace", "search and replace", "find and replace", "substitute",
            "change all", "rename all",
        ]);

        // ===================
        // CODE ANALYSIS
        // ===================
        patterns.insert(TaskType::ListFunctions, vec![
            "list functions", "all functions", "show functions", "functions in",
            "what functions", "function list",
        ]);

        patterns.insert(TaskType::ListClasses, vec![
            "list classes", "all classes", "show classes", "classes in",
            "what classes", "class list",
        ]);

        patterns.insert(TaskType::ListImports, vec![
            "list imports", "all imports", "show imports", "imports in",
            "what imports", "import list", "dependencies",
        ]);

        patterns.insert(TaskType::ShowOutline, vec![
            "outline", "file outline", "show outline", "structure of",
            "overview", "summary of file",
        ]);

        patterns.insert(TaskType::ShowStructure, vec![
            "structure", "project structure", "codebase structure", "architecture",
            "layout", "organization", "how is organized",
        ]);

        patterns.insert(TaskType::ShowDependencies, vec![
            "dependencies", "show dependencies", "what depends on", "dependency tree",
            "dependency graph", "imports", "requires",
        ]);

        patterns.insert(TaskType::CountLines, vec![
            "count lines", "line count", "how many lines", "lines of code",
            "loc", "sloc", "wc -l",
        ]);

        patterns.insert(TaskType::CountFunctions, vec![
            "count functions", "how many functions", "number of functions",
            "function count",
        ]);

        // ===================
        // CODE QUALITY
        // ===================
        patterns.insert(TaskType::Lint, vec![
            "lint", "linter", "eslint", "pylint", "clippy", "rubocop",
            "check style", "style check", "code quality",
        ]);

        patterns.insert(TaskType::Format, vec![
            "format", "formatter", "prettier", "black", "rustfmt", "gofmt",
            "auto format", "fix formatting", "fix indentation",
        ]);

        patterns.insert(TaskType::TypeCheck, vec![
            "type check", "typecheck", "mypy", "typescript check", "tsc",
            "type errors", "typing errors",
        ]);

        patterns.insert(TaskType::CheckSyntax, vec![
            "syntax check", "check syntax", "syntax error", "parse error",
            "compile check",
        ]);

        // ===================
        // GIT OPERATIONS
        // ===================
        exact_matches.insert("git status", TaskType::GitStatus);
        exact_matches.insert("status", TaskType::GitStatus);
        exact_matches.insert("gs", TaskType::GitStatus);
        patterns.insert(TaskType::GitStatus, vec![
            "git status", "status", "what changed", "changes", "modified files",
            "uncommitted", "staged", "unstaged", "working tree",
        ]);

        exact_matches.insert("git diff", TaskType::GitDiff);
        exact_matches.insert("diff", TaskType::GitDiff);
        exact_matches.insert("gd", TaskType::GitDiff);
        patterns.insert(TaskType::GitDiff, vec![
            "git diff", "diff", "show diff", "what's different", "changes",
            "compare", "difference",
        ]);
        exclusions.insert(TaskType::GitDiff, vec!["staged", "cached", "file"]);

        patterns.insert(TaskType::GitDiffStaged, vec![
            "staged diff", "diff staged", "diff cached", "staged changes",
            "what's staged", "ready to commit",
        ]);

        exact_matches.insert("git log", TaskType::GitLog);
        exact_matches.insert("log", TaskType::GitLog);
        exact_matches.insert("gl", TaskType::GitLog);
        patterns.insert(TaskType::GitLog, vec![
            "git log", "log", "history", "commits", "commit history",
            "recent commits", "past commits", "what happened",
        ]);

        patterns.insert(TaskType::GitLogOneline, vec![
            "log oneline", "short log", "compact log", "brief history",
        ]);

        patterns.insert(TaskType::GitBlame, vec![
            "git blame", "blame", "who wrote", "who changed", "who added",
            "who modified", "author of", "when was changed",
        ]);

        patterns.insert(TaskType::GitBranch, vec![
            "branch", "current branch", "what branch", "which branch",
        ]);
        exclusions.insert(TaskType::GitBranch, vec!["create", "delete", "list", "new", "switch"]);

        patterns.insert(TaskType::GitBranchList, vec![
            "branches", "list branches", "all branches", "show branches",
            "branch list", "git branch -a",
        ]);

        patterns.insert(TaskType::GitBranchCreate, vec![
            "create branch", "new branch", "make branch", "add branch",
            "git checkout -b", "git branch ",
        ]);

        patterns.insert(TaskType::GitBranchDelete, vec![
            "delete branch", "remove branch", "drop branch", "git branch -d",
            "git branch -D",
        ]);

        patterns.insert(TaskType::GitCheckout, vec![
            "checkout", "switch to", "go to branch", "change branch",
        ]);

        patterns.insert(TaskType::GitMerge, vec![
            "merge", "git merge", "merge branch", "combine branches",
        ]);

        patterns.insert(TaskType::GitRebase, vec![
            "rebase", "git rebase", "rebase onto", "interactive rebase",
        ]);

        patterns.insert(TaskType::GitStash, vec![
            "stash", "git stash", "save changes", "shelve", "put aside",
        ]);
        exclusions.insert(TaskType::GitStash, vec!["list", "pop", "drop", "apply"]);

        patterns.insert(TaskType::GitStashList, vec![
            "stash list", "list stash", "show stash", "stashes",
        ]);

        patterns.insert(TaskType::GitStashPop, vec![
            "stash pop", "pop stash", "apply stash", "restore stash",
            "get stash back",
        ]);

        patterns.insert(TaskType::GitAdd, vec![
            "stage", "add to staging", "git add",
        ]);
        exclusions.insert(TaskType::GitAdd, vec!["all", "everything"]);

        patterns.insert(TaskType::GitAddAll, vec![
            "stage all", "add all", "git add .", "git add -A", "stage everything",
        ]);

        patterns.insert(TaskType::GitReset, vec![
            "unstage", "reset", "git reset", "remove from staging",
        ]);
        exclusions.insert(TaskType::GitReset, vec!["hard"]);

        patterns.insert(TaskType::GitResetHard, vec![
            "reset hard", "hard reset", "git reset --hard", "discard changes",
            "throw away changes", "undo all changes",
        ]);

        patterns.insert(TaskType::GitCommit, vec![
            "commit", "git commit", "save commit", "create commit",
        ]);
        exclusions.insert(TaskType::GitCommit, vec!["amend"]);

        patterns.insert(TaskType::GitCommitAmend, vec![
            "amend", "git commit --amend", "fix commit", "update commit",
            "change last commit",
        ]);

        patterns.insert(TaskType::GitPush, vec![
            "push", "git push", "upload", "send to remote",
        ]);
        exclusions.insert(TaskType::GitPush, vec!["force"]);

        patterns.insert(TaskType::GitPushForce, vec![
            "force push", "push force", "git push -f", "git push --force",
        ]);

        patterns.insert(TaskType::GitPull, vec![
            "pull", "git pull", "download", "get latest", "update from remote",
            "sync", "fetch and merge",
        ]);

        patterns.insert(TaskType::GitFetch, vec![
            "fetch", "git fetch", "check remote", "get remote changes",
        ]);

        patterns.insert(TaskType::GitClone, vec![
            "clone", "git clone", "download repo", "get repository",
        ]);

        patterns.insert(TaskType::GitInit, vec![
            "init", "git init", "initialize", "create repo", "new repo",
            "start repo",
        ]);

        patterns.insert(TaskType::GitClean, vec![
            "git clean", "clean untracked", "remove untracked",
        ]);

        // ===================
        // BUILD & RUN
        // ===================
        patterns.insert(TaskType::Build, vec![
            "build", "compile", "make", "cargo build", "npm build", "go build",
            "javac", "gcc", "g++",
        ]);
        exclusions.insert(TaskType::Build, vec!["release", "debug", "docker"]);

        patterns.insert(TaskType::BuildRelease, vec![
            "build release", "release build", "production build", "cargo build --release",
            "npm run build:prod", "optimized build",
        ]);

        patterns.insert(TaskType::BuildDebug, vec![
            "build debug", "debug build", "development build", "dev build",
        ]);

        patterns.insert(TaskType::Clean, vec![
            "clean", "cargo clean", "npm clean", "make clean", "clear build",
            "remove build", "delete build",
        ]);

        patterns.insert(TaskType::Run, vec![
            "run", "execute", "start", "launch", "cargo run", "npm start",
            "go run", "python ", "node ",
        ]);
        exclusions.insert(TaskType::Run, vec!["test", "debug"]);

        patterns.insert(TaskType::Dev, vec![
            "dev", "npm run dev", "development", "dev server", "dev mode",
            "hot reload", "watch mode",
        ]);

        patterns.insert(TaskType::Watch, vec![
            "watch", "cargo watch", "npm run watch", "file watcher",
            "auto reload", "live reload",
        ]);

        // ===================
        // TESTING
        // ===================
        patterns.insert(TaskType::Test, vec![
            "test", "run test", "cargo test", "npm test", "pytest", "jest",
            "mocha", "go test", "rspec",
        ]);
        exclusions.insert(TaskType::Test, vec!["all", "coverage", "watch", "file", "function"]);

        patterns.insert(TaskType::TestAll, vec![
            "test all", "all tests", "run all tests", "full test", "complete test",
        ]);

        patterns.insert(TaskType::TestFile, vec![
            "test file", "test this file", "run tests in",
        ]);

        patterns.insert(TaskType::TestFunction, vec![
            "test function", "test this function", "test method", "single test",
        ]);

        patterns.insert(TaskType::TestCoverage, vec![
            "coverage", "test coverage", "code coverage", "coverage report",
        ]);

        patterns.insert(TaskType::TestWatch, vec![
            "test watch", "watch tests", "test on change",
        ]);

        // ===================
        // DEPENDENCIES
        // ===================
        patterns.insert(TaskType::Install, vec![
            "install", "add", "npm install", "pip install", "cargo add",
            "go get", "gem install", "brew install",
        ]);
        exclusions.insert(TaskType::Install, vec!["dev", "development"]);

        patterns.insert(TaskType::InstallDev, vec![
            "install dev", "dev dependency", "npm install -D", "pip install --dev",
        ]);

        patterns.insert(TaskType::Uninstall, vec![
            "uninstall", "remove package", "npm uninstall", "pip uninstall",
            "cargo remove",
        ]);

        patterns.insert(TaskType::Update, vec![
            "update", "upgrade", "npm update", "pip install --upgrade",
            "cargo update",
        ]);

        patterns.insert(TaskType::Outdated, vec![
            "outdated", "npm outdated", "pip list --outdated", "check updates",
        ]);

        patterns.insert(TaskType::Audit, vec![
            "audit", "security audit", "npm audit", "vulnerability",
        ]);
        exclusions.insert(TaskType::Audit, vec!["fix"]);

        patterns.insert(TaskType::AuditFix, vec![
            "audit fix", "fix vulnerabilities", "npm audit fix",
        ]);

        // ===================
        // PROCESSES & PORTS
        // ===================
        patterns.insert(TaskType::ProcessList, vec![
            "ps", "processes", "list processes", "running processes",
            "what's running", "show processes",
        ]);

        patterns.insert(TaskType::ProcessFind, vec![
            "find process", "search process", "process named",
        ]);

        patterns.insert(TaskType::ProcessKill, vec![
            "kill", "kill process", "stop process", "terminate",
        ]);
        exclusions.insert(TaskType::ProcessKill, vec!["port"]);

        patterns.insert(TaskType::ProcessKillByPort, vec![
            "kill port", "free port", "stop port", "kill on port",
            "what's on port", "process on port",
        ]);

        patterns.insert(TaskType::PortList, vec![
            "ports", "list ports", "open ports", "listening ports",
            "used ports", "lsof",
        ]);

        patterns.insert(TaskType::PortFind, vec![
            "what's on port", "port ", "find port", "check port",
        ]);

        // ===================
        // SYSTEM
        // ===================
        patterns.insert(TaskType::SystemInfo, vec![
            "system info", "system information", "about this mac", "uname",
            "os info", "machine info",
        ]);

        patterns.insert(TaskType::DiskUsage, vec![
            "disk usage", "disk space", "du", "storage", "how much space",
            "folder size", "directory size",
        ]);

        patterns.insert(TaskType::DiskFree, vec![
            "disk free", "free space", "df", "available space",
        ]);

        patterns.insert(TaskType::MemoryUsage, vec![
            "memory", "ram", "memory usage", "free memory", "used memory",
        ]);

        patterns.insert(TaskType::CpuUsage, vec![
            "cpu", "cpu usage", "processor", "load average", "top",
        ]);

        patterns.insert(TaskType::EnvList, vec![
            "env", "environment", "environment variables", "printenv",
            "show env", "list env",
        ]);

        patterns.insert(TaskType::EnvGet, vec![
            "get env", "echo $", "env value", "environment variable",
        ]);

        patterns.insert(TaskType::WhichCommand, vec![
            "which", "where is", "path to", "location of", "whereis",
        ]);

        // ===================
        // DOCKER
        // ===================
        patterns.insert(TaskType::DockerPs, vec![
            "docker ps", "containers", "running containers", "docker containers",
        ]);

        patterns.insert(TaskType::DockerImages, vec![
            "docker images", "images", "docker image list",
        ]);

        patterns.insert(TaskType::DockerBuild, vec![
            "docker build", "build image", "build container",
        ]);

        patterns.insert(TaskType::DockerRun, vec![
            "docker run", "run container", "start container",
        ]);

        patterns.insert(TaskType::DockerStop, vec![
            "docker stop", "stop container",
        ]);

        patterns.insert(TaskType::DockerLogs, vec![
            "docker logs", "container logs",
        ]);

        patterns.insert(TaskType::DockerPrune, vec![
            "docker prune", "docker cleanup", "clean docker",
        ]);

        // ===================
        // HTTP/CURL
        // ===================
        patterns.insert(TaskType::HttpGet, vec![
            "curl", "http get", "get url", "fetch url", "download url",
            "wget",
        ]);

        patterns.insert(TaskType::HttpPost, vec![
            "http post", "post to", "send post",
        ]);

        // ===================
        // MISC
        // ===================
        patterns.insert(TaskType::Help, vec![
            "help", "how do i", "how to", "what can you do", "commands",
        ]);

        patterns.insert(TaskType::History, vec![
            "history", "command history", "previous commands", "last commands",
        ]);

        patterns.insert(TaskType::Clear, vec![
            "clear", "cls", "clear screen",
        ]);

        patterns.insert(TaskType::Time, vec![
            "time", "current time", "what time",
        ]);

        patterns.insert(TaskType::Date, vec![
            "date", "today", "what day", "current date",
        ]);

        patterns.insert(TaskType::Calculator, vec![
            "calc", "calculate", "math", "compute", "evaluate",
        ]);

        patterns.insert(TaskType::Shell, vec![
            "shell", "bash", "run command", "execute command", "$",
        ]);

        // ===================
        // PACKAGE MANAGERS (expanded)
        // ===================
        exact_matches.insert("yarn", TaskType::YarnInstall);
        exact_matches.insert("yarn install", TaskType::YarnInstall);
        patterns.insert(TaskType::YarnInstall, vec!["yarn install", "yarn"]);
        patterns.insert(TaskType::YarnAdd, vec!["yarn add"]);
        patterns.insert(TaskType::YarnRemove, vec!["yarn remove"]);
        patterns.insert(TaskType::YarnUpgrade, vec!["yarn upgrade", "yarn update"]);
        patterns.insert(TaskType::YarnDev, vec!["yarn dev"]);
        patterns.insert(TaskType::YarnBuild, vec!["yarn build"]);
        patterns.insert(TaskType::YarnStart, vec!["yarn start"]);

        exact_matches.insert("pnpm install", TaskType::PnpmInstall);
        patterns.insert(TaskType::PnpmInstall, vec!["pnpm install", "pnpm i"]);
        patterns.insert(TaskType::PnpmAdd, vec!["pnpm add"]);
        patterns.insert(TaskType::PnpmRemove, vec!["pnpm remove"]);

        patterns.insert(TaskType::PoetryInstall, vec!["poetry install"]);
        patterns.insert(TaskType::PoetryAdd, vec!["poetry add"]);
        patterns.insert(TaskType::PoetryRemove, vec!["poetry remove"]);
        patterns.insert(TaskType::PoetryUpdate, vec!["poetry update"]);

        patterns.insert(TaskType::PipenvInstall, vec!["pipenv install"]);
        patterns.insert(TaskType::PipenvLock, vec!["pipenv lock"]);

        patterns.insert(TaskType::BunInstall, vec!["bun install", "bun i"]);
        patterns.insert(TaskType::BunAdd, vec!["bun add"]);
        patterns.insert(TaskType::BunRun, vec!["bun run"]);

        // ===================
        // CLOUD/DEVOPS
        // ===================
        patterns.insert(TaskType::AwsCli, vec!["aws", "amazon"]);
        patterns.insert(TaskType::AwsS3Ls, vec!["aws s3 ls", "s3 list", "list s3", "list bucket"]);
        patterns.insert(TaskType::AwsS3Cp, vec!["aws s3 cp", "s3 copy", "copy to s3"]);
        patterns.insert(TaskType::AwsS3Sync, vec!["aws s3 sync", "s3 sync", "sync s3"]);
        patterns.insert(TaskType::AwsEc2List, vec!["aws ec2", "list ec2", "ec2 instances"]);
        patterns.insert(TaskType::AwsLambdaList, vec!["aws lambda list", "list lambda", "lambdas"]);
        patterns.insert(TaskType::AwsLambdaInvoke, vec!["aws lambda invoke", "invoke lambda", "run lambda"]);

        patterns.insert(TaskType::GcloudList, vec!["gcloud", "gcp", "google cloud"]);
        patterns.insert(TaskType::GcloudDeploy, vec!["gcloud deploy", "gcp deploy"]);
        patterns.insert(TaskType::AzureCli, vec!["az ", "azure"]);

        exact_matches.insert("kubectl get pods", TaskType::KubectlGet);
        exact_matches.insert("k get pods", TaskType::KubectlGet);
        patterns.insert(TaskType::KubectlGet, vec!["kubectl get", "k get", "kube get"]);
        patterns.insert(TaskType::KubectlDescribe, vec!["kubectl describe", "k describe"]);
        patterns.insert(TaskType::KubectlLogs, vec!["kubectl logs", "k logs", "pod logs"]);
        patterns.insert(TaskType::KubectlApply, vec!["kubectl apply", "k apply"]);
        patterns.insert(TaskType::KubectlDelete, vec!["kubectl delete", "k delete"]);
        patterns.insert(TaskType::KubectlExec, vec!["kubectl exec", "k exec"]);
        patterns.insert(TaskType::KubectlPortForward, vec!["kubectl port-forward", "k port-forward"]);

        patterns.insert(TaskType::HelmInstall, vec!["helm install"]);
        patterns.insert(TaskType::HelmUpgrade, vec!["helm upgrade"]);
        patterns.insert(TaskType::HelmList, vec!["helm list", "helm ls"]);
        patterns.insert(TaskType::HelmUninstall, vec!["helm uninstall", "helm delete"]);

        patterns.insert(TaskType::TerraformInit, vec!["terraform init", "tf init"]);
        patterns.insert(TaskType::TerraformPlan, vec!["terraform plan", "tf plan"]);
        patterns.insert(TaskType::TerraformApply, vec!["terraform apply", "tf apply"]);
        patterns.insert(TaskType::TerraformDestroy, vec!["terraform destroy", "tf destroy"]);

        patterns.insert(TaskType::AnsiblePlaybook, vec!["ansible-playbook", "ansible playbook"]);
        patterns.insert(TaskType::AnsibleInventory, vec!["ansible-inventory", "ansible inventory"]);

        // ===================
        // ADVANCED GIT
        // ===================
        patterns.insert(TaskType::GitBisect, vec!["git bisect", "bisect"]);
        patterns.insert(TaskType::GitBisectStart, vec!["git bisect start", "bisect start"]);
        patterns.insert(TaskType::GitBisectGood, vec!["git bisect good", "bisect good"]);
        patterns.insert(TaskType::GitBisectBad, vec!["git bisect bad", "bisect bad"]);
        patterns.insert(TaskType::GitBisectReset, vec!["git bisect reset", "bisect reset"]);
        patterns.insert(TaskType::GitWorktree, vec!["git worktree", "worktree"]);
        patterns.insert(TaskType::GitWorktreeAdd, vec!["git worktree add", "worktree add"]);
        patterns.insert(TaskType::GitWorktreeList, vec!["git worktree list", "worktree list"]);
        patterns.insert(TaskType::GitReflog, vec!["git reflog", "reflog"]);
        patterns.insert(TaskType::GitFsck, vec!["git fsck", "fsck"]);
        patterns.insert(TaskType::GitSubmodule, vec!["git submodule", "submodule"]);
        patterns.insert(TaskType::GitSubmoduleUpdate, vec!["git submodule update", "submodule update"]);
        patterns.insert(TaskType::GitLfs, vec!["git lfs", "lfs"]);
        patterns.insert(TaskType::GitLfsPull, vec!["git lfs pull", "lfs pull"]);
        patterns.insert(TaskType::GitLfsPush, vec!["git lfs push", "lfs push"]);
        patterns.insert(TaskType::GitArchive, vec!["git archive", "archive"]);
        patterns.insert(TaskType::GitBundle, vec!["git bundle", "bundle"]);
        patterns.insert(TaskType::GitShortlog, vec!["git shortlog", "shortlog"]);
        patterns.insert(TaskType::GitDescribe, vec!["git describe", "describe"]);
        patterns.insert(TaskType::GitNotes, vec!["git notes", "notes"]);

        // ===================
        // DEBUGGING/PROFILING
        // ===================
        patterns.insert(TaskType::LldbRun, vec!["lldb", "lldb run"]);
        patterns.insert(TaskType::LldbAttach, vec!["lldb attach", "lldb -p"]);
        patterns.insert(TaskType::GdbRun, vec!["gdb", "gdb run"]);
        patterns.insert(TaskType::GdbAttach, vec!["gdb attach", "gdb -p"]);
        patterns.insert(TaskType::Valgrind, vec!["valgrind", "memory check"]);
        patterns.insert(TaskType::Strace, vec!["strace", "trace syscalls"]);
        patterns.insert(TaskType::Dtrace, vec!["dtrace"]);
        patterns.insert(TaskType::PerfRecord, vec!["perf record", "perf"]);
        patterns.insert(TaskType::PerfReport, vec!["perf report"]);
        patterns.insert(TaskType::Flamegraph, vec!["flamegraph", "flame graph"]);
        patterns.insert(TaskType::HeapProfile, vec!["heap profile", "memory profile", "heaptrack"]);
        patterns.insert(TaskType::CpuProfile, vec!["cpu profile", "profile cpu"]);
        patterns.insert(TaskType::MemoryProfile, vec!["memory profile", "profile memory"]);

        // ===================
        // SECURITY SCANNING
        // ===================
        patterns.insert(TaskType::TrivyScan, vec!["trivy", "trivy scan"]);
        patterns.insert(TaskType::SnykTest, vec!["snyk", "snyk test"]);
        patterns.insert(TaskType::BanditScan, vec!["bandit", "python security"]);
        patterns.insert(TaskType::SafetyCheck, vec!["safety", "safety check"]);
        patterns.insert(TaskType::NpmAuditFix, vec!["npm audit fix"]);
        patterns.insert(TaskType::CargoAuditFix, vec!["cargo audit fix"]);
        patterns.insert(TaskType::OsvScanner, vec!["osv-scanner", "osv scan"]);
        patterns.insert(TaskType::GitleaksScan, vec!["gitleaks", "secrets scan"]);
        patterns.insert(TaskType::SemgrepScan, vec!["semgrep", "sast scan"]);

        // ===================
        // DOCUMENTATION
        // ===================
        patterns.insert(TaskType::Rustdoc, vec!["rustdoc", "cargo doc"]);
        patterns.insert(TaskType::Jsdoc, vec!["jsdoc"]);
        patterns.insert(TaskType::Typedoc, vec!["typedoc"]);
        patterns.insert(TaskType::Sphinx, vec!["sphinx", "sphinx-build"]);
        patterns.insert(TaskType::Mkdocs, vec!["mkdocs"]);
        patterns.insert(TaskType::Docusaurus, vec!["docusaurus"]);
        patterns.insert(TaskType::Storybook, vec!["storybook"]);

        // ===================
        // DATABASE CLI
        // ===================
        patterns.insert(TaskType::PsqlConnect, vec!["psql", "postgres connect", "postgresql"]);
        patterns.insert(TaskType::PsqlQuery, vec!["psql -c", "postgres query"]);
        patterns.insert(TaskType::PsqlList, vec!["psql -l", "postgres list", "\\l"]);
        patterns.insert(TaskType::MysqlConnect, vec!["mysql", "mysql connect"]);
        patterns.insert(TaskType::MysqlQuery, vec!["mysql -e", "mysql query"]);
        patterns.insert(TaskType::MysqlList, vec!["mysql list", "show databases"]);
        patterns.insert(TaskType::SqliteQuery, vec!["sqlite3", "sqlite"]);
        patterns.insert(TaskType::SqliteList, vec!["sqlite list", ".tables"]);
        patterns.insert(TaskType::RedisConnect, vec!["redis-cli", "redis connect"]);
        patterns.insert(TaskType::RedisCli, vec!["redis"]);
        patterns.insert(TaskType::RedisGet, vec!["redis get"]);
        patterns.insert(TaskType::RedisSet, vec!["redis set"]);
        patterns.insert(TaskType::RedisKeys, vec!["redis keys"]);
        patterns.insert(TaskType::MongoConnect, vec!["mongosh", "mongo connect", "mongodb"]);
        patterns.insert(TaskType::MongoshQuery, vec!["mongosh query", "mongo query"]);
        patterns.insert(TaskType::MongoList, vec!["mongo list", "show dbs"]);

        // ===================
        // TMUX/SCREEN
        // ===================
        patterns.insert(TaskType::TmuxNew, vec!["tmux new", "tmux", "new session"]);
        patterns.insert(TaskType::TmuxList, vec!["tmux ls", "tmux list", "list sessions"]);
        patterns.insert(TaskType::TmuxAttach, vec!["tmux attach", "tmux a"]);
        patterns.insert(TaskType::TmuxKill, vec!["tmux kill", "kill session"]);
        patterns.insert(TaskType::TmuxSplit, vec!["tmux split"]);
        patterns.insert(TaskType::TmuxSend, vec!["tmux send"]);
        patterns.insert(TaskType::ScreenNew, vec!["screen", "screen new"]);
        patterns.insert(TaskType::ScreenList, vec!["screen -ls", "screen list"]);
        patterns.insert(TaskType::ScreenAttach, vec!["screen -r", "screen attach"]);

        // ===================
        // SSH/REMOTE
        // ===================
        patterns.insert(TaskType::SshConnect, vec!["ssh", "ssh connect"]);
        patterns.insert(TaskType::SshCopy, vec!["ssh-copy-id", "copy ssh key"]);
        patterns.insert(TaskType::SshTunnel, vec!["ssh tunnel", "ssh -L"]);
        patterns.insert(TaskType::ScpCopy, vec!["scp", "secure copy"]);
        patterns.insert(TaskType::RsyncSync, vec!["rsync", "sync files"]);
        patterns.insert(TaskType::SftpConnect, vec!["sftp"]);

        // ===================
        // LOG ANALYSIS
        // ===================
        patterns.insert(TaskType::TailFollow, vec!["tail -f", "follow log", "watch log"]);
        patterns.insert(TaskType::TailLines, vec!["tail -n", "last lines", "tail"]);
        patterns.insert(TaskType::Journalctl, vec!["journalctl", "system log"]);
        patterns.insert(TaskType::JournalctlFollow, vec!["journalctl -f", "follow journal"]);
        patterns.insert(TaskType::LogGrep, vec!["grep log", "search log"]);
        patterns.insert(TaskType::LogParse, vec!["parse log", "analyze log"]);
        patterns.insert(TaskType::AwsLogs, vec!["aws logs", "cloudwatch"]);

        // ===================
        // FRAMEWORK SPECIFIC
        // ===================
        patterns.insert(TaskType::DjangoManage, vec!["python manage.py", "django manage"]);
        patterns.insert(TaskType::DjangoMigrate, vec!["django migrate", "python manage.py migrate"]);
        patterns.insert(TaskType::DjangoShell, vec!["django shell", "python manage.py shell"]);
        patterns.insert(TaskType::DjangoTest, vec!["django test", "python manage.py test"]);
        patterns.insert(TaskType::RailsConsole, vec!["rails console", "rails c"]);
        patterns.insert(TaskType::RailsServer, vec!["rails server", "rails s"]);
        patterns.insert(TaskType::RailsMigrate, vec!["rails migrate", "rake db:migrate"]);
        patterns.insert(TaskType::RailsGenerate, vec!["rails generate", "rails g"]);
        exact_matches.insert("next dev", TaskType::NextDev);
        patterns.insert(TaskType::NextDev, vec!["next dev", "nextjs dev"]);
        patterns.insert(TaskType::NextBuild, vec!["next build", "nextjs build"]);
        patterns.insert(TaskType::NextStart, vec!["next start", "nextjs start"]);
        patterns.insert(TaskType::NuxtDev, vec!["nuxt dev", "nuxtjs dev"]);
        patterns.insert(TaskType::NuxtBuild, vec!["nuxt build", "nuxtjs build"]);
        patterns.insert(TaskType::ViteDev, vec!["vite dev", "vite"]);
        patterns.insert(TaskType::ViteBuild, vec!["vite build"]);
        patterns.insert(TaskType::CreateReactApp, vec!["create-react-app", "cra"]);
        patterns.insert(TaskType::AngularServe, vec!["ng serve", "angular serve"]);
        patterns.insert(TaskType::AngularBuild, vec!["ng build", "angular build"]);
        patterns.insert(TaskType::FlutterRun, vec!["flutter run"]);
        patterns.insert(TaskType::FlutterBuild, vec!["flutter build"]);
        patterns.insert(TaskType::ExpoStart, vec!["expo start"]);
        patterns.insert(TaskType::ReactNativeStart, vec!["react-native start", "npx react-native"]);

        // ===================
        // COMPOUND COMMANDS
        // ===================
        patterns.insert(TaskType::CommitAndPush, vec![
            "commit and push", "commit push", "commit then push", "save and push",
        ]);
        patterns.insert(TaskType::BuildAndTest, vec![
            "build and test", "build test", "build then test",
        ]);
        patterns.insert(TaskType::BuildAndRun, vec![
            "build and run", "build run", "compile and run",
        ]);
        patterns.insert(TaskType::PullAndBuild, vec![
            "pull and build", "update and build", "pull then build",
        ]);
        patterns.insert(TaskType::CleanAndBuild, vec![
            "clean and build", "clean build", "rebuild clean",
        ]);
        patterns.insert(TaskType::TestAndCoverage, vec![
            "test and coverage", "test coverage", "test with coverage",
        ]);
        patterns.insert(TaskType::LintAndFix, vec![
            "lint and fix", "lint fix", "fix lint",
        ]);
        patterns.insert(TaskType::FormatAndCommit, vec![
            "format and commit", "format commit",
        ]);

        // ===================
        // CONTEXT-AWARE
        // ===================
        exact_matches.insert("!!", TaskType::RunAgain);
        exact_matches.insert("again", TaskType::RunAgain);
        exact_matches.insert("retry", TaskType::Retry);
        exact_matches.insert("undo", TaskType::Undo);
        exact_matches.insert("cd -", TaskType::CdBack);
        patterns.insert(TaskType::RunAgain, vec!["run again", "do again", "repeat", "!!"]);
        patterns.insert(TaskType::Undo, vec!["undo", "revert"]);
        patterns.insert(TaskType::Retry, vec!["retry", "try again"]);
        patterns.insert(TaskType::LastCommand, vec!["last command", "previous command"]);
        patterns.insert(TaskType::EditLastFile, vec!["edit last", "open last file"]);
        patterns.insert(TaskType::CdBack, vec!["cd -", "go back", "previous directory"]);
        patterns.insert(TaskType::CdPrevious, vec!["cd ..", "parent directory", "up"]);

        // ===================
        // MORE MISC
        // ===================
        patterns.insert(TaskType::Uuid, vec!["uuid", "generate uuid", "new uuid"]);
        patterns.insert(TaskType::Base64Encode, vec!["base64 encode", "encode base64"]);
        patterns.insert(TaskType::Base64Decode, vec!["base64 decode", "decode base64"]);
        patterns.insert(TaskType::Md5Sum, vec!["md5", "md5sum"]);
        patterns.insert(TaskType::Sha256Sum, vec!["sha256", "sha256sum"]);
        patterns.insert(TaskType::JsonFormat, vec!["json format", "format json", "pretty json", "jq"]);
        patterns.insert(TaskType::JsonValidate, vec!["json validate", "validate json"]);
        patterns.insert(TaskType::XmlFormat, vec!["xml format", "format xml"]);
        patterns.insert(TaskType::YamlToJson, vec!["yaml to json", "convert yaml"]);
        patterns.insert(TaskType::JsonToYaml, vec!["json to yaml", "convert json yaml"]);
        patterns.insert(TaskType::UrlEncode, vec!["url encode", "urlencode"]);
        patterns.insert(TaskType::UrlDecode, vec!["url decode", "urldecode"]);
        patterns.insert(TaskType::Hostname, vec!["hostname"]);
        patterns.insert(TaskType::Whoami, vec!["whoami", "who am i"]);
        patterns.insert(TaskType::Uptime, vec!["uptime"]);

        // ===================
        // NETWORK
        // ===================
        patterns.insert(TaskType::Ping, vec!["ping"]);
        patterns.insert(TaskType::Traceroute, vec!["traceroute", "tracert"]);
        patterns.insert(TaskType::Dig, vec!["dig", "dns lookup"]);
        patterns.insert(TaskType::Nslookup, vec!["nslookup"]);
        patterns.insert(TaskType::Netstat, vec!["netstat"]);
        patterns.insert(TaskType::Ss, vec!["ss "]);
        patterns.insert(TaskType::Ifconfig, vec!["ifconfig"]);
        patterns.insert(TaskType::IpAddr, vec!["ip addr", "ip address"]);
        patterns.insert(TaskType::Arp, vec!["arp"]);
        patterns.insert(TaskType::Nmap, vec!["nmap", "port scan"]);
        patterns.insert(TaskType::Tcpdump, vec!["tcpdump", "packet capture"]);

        // ===================
        // MEDIA/FILES
        // ===================
        patterns.insert(TaskType::ImageInfo, vec!["image info", "identify", "exif"]);
        patterns.insert(TaskType::ImageResize, vec!["resize image", "scale image"]);
        patterns.insert(TaskType::ImageConvert, vec!["convert image", "image convert"]);
        patterns.insert(TaskType::VideoInfo, vec!["video info", "ffprobe"]);
        patterns.insert(TaskType::AudioInfo, vec!["audio info"]);
        patterns.insert(TaskType::PdfInfo, vec!["pdf info", "pdfinfo"]);
        patterns.insert(TaskType::PdfMerge, vec!["pdf merge", "merge pdf", "combine pdf"]);
        patterns.insert(TaskType::PdfSplit, vec!["pdf split", "split pdf"]);

        Self {
            patterns,
            exact_matches,
            exclusions,
        }
    }

    pub fn classify(&self, input: &str) -> (TaskType, f32) {
        let input_lower = input.to_lowercase().trim().to_string();

        // Check exact matches first
        if let Some(task) = self.exact_matches.get(input_lower.as_str()) {
            return (*task, 1.0);
        }

        // Score each task type
        let mut scores: Vec<(TaskType, f32)> = Vec::new();

        for (task_type, keywords) in &self.patterns {
            let mut score = 0.0f32;
            let mut matched = false;

            // Check exclusions first
            if let Some(excl) = self.exclusions.get(task_type) {
                let has_exclusion = excl.iter().any(|e| input_lower.contains(e));
                if has_exclusion {
                    continue;
                }
            }

            // Score keywords
            for keyword in keywords {
                if input_lower.contains(keyword) {
                    // Longer matches are worth more
                    score += keyword.len() as f32;
                    // Exact word boundary matches are worth even more
                    if input_lower.starts_with(keyword) || input_lower.ends_with(keyword) {
                        score += 5.0;
                    }
                    matched = true;
                }
            }

            if matched {
                scores.push((*task_type, score));
            }
        }

        // Sort by score descending
        scores.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap_or(std::cmp::Ordering::Equal));

        if let Some((task, score)) = scores.first() {
            let confidence = (score / 30.0).min(1.0);
            (*task, confidence)
        } else {
            (TaskType::Shell, 0.1)
        }
    }
}

// =============================================================================
// SMART ENTITY EXTRACTOR
// =============================================================================

pub struct SmartExtractor {
    path_regex: Regex,
    quoted_regex: Regex,
    glob_regex: Regex,
    number_regex: Regex,
    url_regex: Regex,
    branch_regex: Regex,
    port_regex: Regex,
}

impl SmartExtractor {
    pub fn new() -> Self {
        Self {
            path_regex: Regex::new(r"(?:^|\s)([~/.][\w\-./]+)").unwrap(),
            quoted_regex: Regex::new(r#"["']([^"']+)["']"#).unwrap(),
            glob_regex: Regex::new(r"(\*\*?\.?[\w*]+|\*\.[\w]+)").unwrap(),
            number_regex: Regex::new(r"\b(\d+)\b").unwrap(),
            url_regex: Regex::new(r"(https?://[^\s]+)").unwrap(),
            branch_regex: Regex::new(r"(?:branch|checkout|switch|merge)\s+(\S+)").unwrap(),
            port_regex: Regex::new(r"(?:port|:)(\d{2,5})").unwrap(),
        }
    }

    pub fn extract_all(&self, input: &str) -> ExtractedEntities {
        ExtractedEntities {
            paths: self.extract_paths(input),
            quoted: self.extract_quoted(input),
            glob: self.extract_glob(input),
            numbers: self.extract_numbers(input),
            urls: self.extract_urls(input),
            branch: self.extract_branch(input),
            port: self.extract_port(input),
            search_term: self.extract_search_term(input),
            message: self.extract_message(input),
        }
    }

    fn extract_paths(&self, input: &str) -> Vec<String> {
        let mut paths = Vec::new();

        // Quoted paths first (highest priority)
        for cap in self.quoted_regex.captures_iter(input) {
            if let Some(m) = cap.get(1) {
                let p = m.as_str();
                if p.contains('/') || p.contains('.') {
                    paths.push(p.to_string());
                }
            }
        }

        // Unquoted paths
        for cap in self.path_regex.captures_iter(input) {
            if let Some(m) = cap.get(1) {
                let p = m.as_str().to_string();
                if !paths.contains(&p) {
                    paths.push(p);
                }
            }
        }

        paths
    }

    fn extract_quoted(&self, input: &str) -> Vec<String> {
        self.quoted_regex
            .captures_iter(input)
            .filter_map(|cap| cap.get(1).map(|m| m.as_str().to_string()))
            .collect()
    }

    fn extract_glob(&self, input: &str) -> Option<String> {
        self.glob_regex
            .captures(input)
            .and_then(|cap| cap.get(1).map(|m| m.as_str().to_string()))
    }

    fn extract_numbers(&self, input: &str) -> Vec<i64> {
        self.number_regex
            .captures_iter(input)
            .filter_map(|cap| cap.get(1).and_then(|m| m.as_str().parse().ok()))
            .collect()
    }

    fn extract_urls(&self, input: &str) -> Vec<String> {
        self.url_regex
            .captures_iter(input)
            .filter_map(|cap| cap.get(1).map(|m| m.as_str().to_string()))
            .collect()
    }

    fn extract_branch(&self, input: &str) -> Option<String> {
        self.branch_regex
            .captures(input)
            .and_then(|cap| cap.get(1).map(|m| m.as_str().to_string()))
    }

    fn extract_port(&self, input: &str) -> Option<u16> {
        self.port_regex
            .captures(input)
            .and_then(|cap| cap.get(1).and_then(|m| m.as_str().parse().ok()))
    }

    fn extract_search_term(&self, input: &str) -> Option<String> {
        // Quoted term
        if let Some(cap) = self.quoted_regex.captures(input) {
            return cap.get(1).map(|m| m.as_str().to_string());
        }

        // "for X" pattern
        let for_re = Regex::new(r"(?:for|find|search|grep)\s+(\w+)").unwrap();
        if let Some(cap) = for_re.captures(input) {
            return cap.get(1).map(|m| m.as_str().to_string());
        }

        // "named X" pattern
        let named_re = Regex::new(r"(?:named|called)\s+(\w+)").unwrap();
        if let Some(cap) = named_re.captures(input) {
            return cap.get(1).map(|m| m.as_str().to_string());
        }

        None
    }

    fn extract_message(&self, input: &str) -> Option<String> {
        // Commit message after -m
        let msg_re = Regex::new(r#"-m\s*["']([^"']+)["']"#).unwrap();
        if let Some(cap) = msg_re.captures(input) {
            return cap.get(1).map(|m| m.as_str().to_string());
        }

        // Message after "message" or "msg"
        let msg_re2 = Regex::new(r#"(?:message|msg)\s*["']([^"']+)["']"#).unwrap();
        if let Some(cap) = msg_re2.captures(input) {
            return cap.get(1).map(|m| m.as_str().to_string());
        }

        // Quoted string at end might be a message
        if let Some(cap) = self.quoted_regex.captures(input) {
            return cap.get(1).map(|m| m.as_str().to_string());
        }

        None
    }
}

#[derive(Debug, Clone, Default)]
pub struct ExtractedEntities {
    pub paths: Vec<String>,
    pub quoted: Vec<String>,
    pub glob: Option<String>,
    pub numbers: Vec<i64>,
    pub urls: Vec<String>,
    pub branch: Option<String>,
    pub port: Option<u16>,
    pub search_term: Option<String>,
    pub message: Option<String>,
}

impl ExtractedEntities {
    pub fn path(&self) -> Option<&str> {
        self.paths.first().map(|s| s.as_str())
    }

    pub fn search(&self) -> Option<&str> {
        self.search_term.as_deref()
            .or_else(|| self.quoted.first().map(|s| s.as_str()))
    }
}

// =============================================================================
// WORKFLOW ENGINE V2
// =============================================================================

pub struct WorkflowEngineV2;

impl WorkflowEngineV2 {
    pub fn get_command(task: TaskType, entities: &ExtractedEntities, raw_input: &str) -> Option<String> {
        let path = entities.path().unwrap_or(".");
        let search = entities.search().unwrap_or("");
        let glob = entities.glob.as_deref().unwrap_or("*");
        let branch = entities.branch.as_deref().unwrap_or("main");
        let port = entities.port.unwrap_or(3000);
        let message = entities.message.as_deref().unwrap_or("Update");

        let cmd = match task {
            // FILE OPERATIONS
            TaskType::FindFiles => format!("find {} -name '{}' 2>/dev/null | head -100", path, glob),
            TaskType::ReadFile => format!("cat '{}'", path),
            TaskType::ListDirectory => format!("ls -la {}", path),
            TaskType::TreeView => format!("find {} -type f | head -200 | sort", path),
            TaskType::FileInfo => format!("stat '{}'", path),
            TaskType::FileSize => format!("du -sh '{}'", path),
            TaskType::FindLargeFiles => format!("find {} -type f -size +10M 2>/dev/null | head -20", path),
            TaskType::FindRecentFiles => format!("find {} -type f -mtime -1 2>/dev/null | head -50", path),
            TaskType::CreateDirectory => format!("mkdir -p '{}'", path),
            TaskType::DeleteFile => format!("rm -i '{}'", path),
            TaskType::MoveFile => {
                if entities.paths.len() >= 2 {
                    format!("mv '{}' '{}'", entities.paths[0], entities.paths[1])
                } else {
                    return None;
                }
            }
            TaskType::CopyFile => {
                if entities.paths.len() >= 2 {
                    format!("cp '{}' '{}'", entities.paths[0], entities.paths[1])
                } else {
                    return None;
                }
            }
            TaskType::ExtractArchive => format!("unar '{}' -o '{}'", path, path.trim_end_matches(|c| c != '/').trim_end_matches('/')),
            TaskType::CompressFile => format!("zip -r '{}.zip' '{}'", path, path),

            // CODE SEARCH
            TaskType::SearchText => format!("grep -rn '{}' {} 2>/dev/null | head -100", search, path),
            TaskType::SearchRegex => format!("grep -rPn '{}' {} 2>/dev/null | head -100", search, path),
            TaskType::SearchFunction => format!(
                "grep -rn -E '^[[:space:]]*(pub )?(async )?(fn |def |func |function |const |let ){}' {} 2>/dev/null | head -50",
                search, path
            ),
            TaskType::SearchClass => format!(
                "grep -rn -E '^[[:space:]]*(pub )?(class |struct |type |interface |enum ){}' {} 2>/dev/null | head -50",
                search, path
            ),
            TaskType::SearchVariable => format!(
                "grep -rn -E '(const |let |var |static ){}' {} 2>/dev/null | head -50",
                search, path
            ),
            TaskType::SearchImport => format!(
                "grep -rn -E '(import |from |require|use ).*{}' {} 2>/dev/null | head -50",
                search, path
            ),
            TaskType::SearchTodo => format!("grep -rn -i 'TODO' {} 2>/dev/null | head -100", path),
            TaskType::SearchFixme => format!("grep -rn -i 'FIXME' {} 2>/dev/null | head -100", path),
            TaskType::SearchError => format!("grep -rn -iE '(error|bug|issue|problem)' {} 2>/dev/null | head -100", path),
            TaskType::FindReferences => format!("grep -rn '{}' {} 2>/dev/null | head -100", search, path),
            TaskType::FindDefinition => format!(
                "grep -rn -E '^[[:space:]]*(pub )?(fn |def |class |struct |const ){}' {} 2>/dev/null | head -20",
                search, path
            ),
            TaskType::SearchAndReplace => {
                if entities.quoted.len() >= 2 {
                    format!("sed -i '' 's/{}/{}/g' {}", entities.quoted[0], entities.quoted[1], path)
                } else {
                    return None;
                }
            }

            // CODE ANALYSIS
            TaskType::ListFunctions => format!(
                "grep -n -E '^[[:space:]]*(pub )?(async )?(fn |def |func |function )' {} 2>/dev/null | head -100",
                path
            ),
            TaskType::ListClasses => format!(
                "grep -n -E '^[[:space:]]*(pub )?(class |struct |type |interface |enum )' {} 2>/dev/null | head -100",
                path
            ),
            TaskType::ListImports => format!(
                "grep -n -E '^(import |from |require|use )' {} 2>/dev/null | head -100",
                path
            ),
            TaskType::ShowOutline => format!(
                "grep -n -E '^[[:space:]]*(pub )?(async )?(fn |def |class |struct |impl |mod |const |type )' {} 2>/dev/null",
                path
            ),
            TaskType::ShowStructure => format!(
                "find {} -type f \\( -name '*.py' -o -name '*.rs' -o -name '*.js' -o -name '*.ts' -o -name '*.go' -o -name '*.java' \\) 2>/dev/null | head -200 | sort",
                path
            ),
            TaskType::ShowDependencies => {
                format!("cat {}/package.json 2>/dev/null || cat {}/Cargo.toml 2>/dev/null || cat {}/requirements.txt 2>/dev/null || cat {}/go.mod 2>/dev/null || echo 'No dependency file found'", path, path, path, path)
            }
            TaskType::CountLines => format!("wc -l {} 2>/dev/null || find {} -type f -name '*.rs' -o -name '*.py' -o -name '*.js' | xargs wc -l 2>/dev/null", path, path),
            TaskType::CountFunctions => format!(
                "grep -c -E '^[[:space:]]*(pub )?(async )?(fn |def |func |function )' {} 2>/dev/null || echo '0'",
                path
            ),

            // CODE QUALITY
            TaskType::Lint => format!(
                "cd {} && (cargo clippy 2>&1 || eslint . 2>&1 || pylint . 2>&1 || echo 'No linter found')",
                path
            ),
            TaskType::Format => format!(
                "cd {} && (cargo fmt 2>&1 || npx prettier --write . 2>&1 || black . 2>&1 || echo 'No formatter found')",
                path
            ),
            TaskType::TypeCheck => format!(
                "cd {} && (npx tsc --noEmit 2>&1 || mypy . 2>&1 || echo 'No type checker found')",
                path
            ),
            TaskType::CheckSyntax => format!(
                "cd {} && (cargo check 2>&1 || python -m py_compile {} 2>&1 || node --check {} 2>&1 || echo 'Syntax check not available')",
                path, path, path
            ),

            // GIT OPERATIONS
            TaskType::GitStatus => "git status".to_string(),
            TaskType::GitDiff => "git diff".to_string(),
            TaskType::GitDiffStaged => "git diff --staged".to_string(),
            TaskType::GitDiffFile => format!("git diff '{}'", path),
            TaskType::GitLog => "git log --oneline -30".to_string(),
            TaskType::GitLogFile => format!("git log --oneline '{}' | head -30", path),
            TaskType::GitLogOneline => "git log --oneline -50".to_string(),
            TaskType::GitBlame => format!("git blame '{}'", path),
            TaskType::GitShow => "git show".to_string(),
            TaskType::GitBranch => "git branch --show-current".to_string(),
            TaskType::GitBranchList => "git branch -a".to_string(),
            TaskType::GitBranchCreate => format!("git checkout -b '{}'", branch),
            TaskType::GitBranchDelete => format!("git branch -d '{}'", branch),
            TaskType::GitBranchRename => format!("git branch -m '{}'", branch),
            TaskType::GitCheckout => format!("git checkout '{}'", branch),
            TaskType::GitCheckoutFile => format!("git checkout -- '{}'", path),
            TaskType::GitSwitch => format!("git switch '{}'", branch),
            TaskType::GitMerge => format!("git merge '{}'", branch),
            TaskType::GitRebase => format!("git rebase '{}'", branch),
            TaskType::GitCherryPick => {
                if let Some(hash) = entities.quoted.first() {
                    format!("git cherry-pick '{}'", hash)
                } else {
                    return None;
                }
            }
            TaskType::GitStash => "git stash".to_string(),
            TaskType::GitStashList => "git stash list".to_string(),
            TaskType::GitStashPop => "git stash pop".to_string(),
            TaskType::GitStashDrop => "git stash drop".to_string(),
            TaskType::GitAdd => format!("git add '{}'", path),
            TaskType::GitAddAll => "git add -A".to_string(),
            TaskType::GitAddFile => format!("git add '{}'", path),
            TaskType::GitReset => "git reset".to_string(),
            TaskType::GitResetFile => format!("git reset '{}'", path),
            TaskType::GitResetHard => "git reset --hard".to_string(),
            TaskType::GitRevert => "git revert HEAD".to_string(),
            TaskType::GitCommit => format!("git commit -m '{}'", message),
            TaskType::GitCommitAmend => "git commit --amend".to_string(),
            TaskType::GitPush => "git push".to_string(),
            TaskType::GitPushForce => "git push --force".to_string(),
            TaskType::GitPull => "git pull".to_string(),
            TaskType::GitFetch => "git fetch --all".to_string(),
            TaskType::GitClone => {
                if let Some(url) = entities.urls.first() {
                    format!("git clone '{}'", url)
                } else {
                    return None;
                }
            }
            TaskType::GitInit => "git init".to_string(),
            TaskType::GitRemote => "git remote -v".to_string(),
            TaskType::GitTag => "git tag".to_string(),
            TaskType::GitTagCreate => format!("git tag '{}'", entities.quoted.first().unwrap_or(&"v1.0.0".to_string())),
            TaskType::GitTagDelete => format!("git tag -d '{}'", entities.quoted.first().unwrap_or(&"".to_string())),
            TaskType::GitClean => "git clean -fd".to_string(),
            TaskType::GitGc => "git gc".to_string(),

            // BUILD & RUN
            TaskType::Build => format!(
                "cd {} && (cargo build 2>&1 || npm run build 2>&1 || go build 2>&1 || make 2>&1 || echo 'No build system found')",
                path
            ),
            TaskType::BuildRelease => format!(
                "cd {} && (cargo build --release 2>&1 || npm run build:prod 2>&1 || go build -ldflags='-s -w' 2>&1 || echo 'No build system found')",
                path
            ),
            TaskType::BuildDebug => format!("cd {} && cargo build 2>&1 || npm run build:dev 2>&1", path),
            TaskType::Clean => format!(
                "cd {} && (cargo clean 2>&1 || rm -rf node_modules 2>&1 || make clean 2>&1 || echo 'Cleaned')",
                path
            ),
            TaskType::Rebuild => format!(
                "cd {} && (cargo clean && cargo build 2>&1 || rm -rf node_modules && npm install && npm run build 2>&1)",
                path
            ),
            TaskType::Run => format!(
                "cd {} && (cargo run 2>&1 || npm start 2>&1 || go run . 2>&1 || python main.py 2>&1 || echo 'No run command found')",
                path
            ),
            TaskType::RunDebug => format!("cd {} && cargo run 2>&1 || npm run dev 2>&1", path),
            TaskType::RunRelease => format!("cd {} && cargo run --release 2>&1", path),
            TaskType::Watch => format!(
                "cd {} && (cargo watch -x run 2>&1 || npm run watch 2>&1 || echo 'No watch command found')",
                path
            ),
            TaskType::Dev => format!(
                "cd {} && (npm run dev 2>&1 || cargo watch -x run 2>&1 || echo 'No dev command found')",
                path
            ),
            TaskType::Start => format!("cd {} && npm start 2>&1 || cargo run 2>&1", path),
            TaskType::Stop => "pkill -f 'npm\\|cargo\\|node' || echo 'No process to stop'".to_string(),
            TaskType::Restart => format!("cd {} && npm restart 2>&1 || (pkill -f cargo && cargo run 2>&1)", path),

            // TESTING
            TaskType::Test => format!(
                "cd {} && (cargo test 2>&1 || npm test 2>&1 || pytest 2>&1 || go test ./... 2>&1 || echo 'No test command found')",
                path
            ),
            TaskType::TestAll => format!(
                "cd {} && (cargo test --all 2>&1 || npm test -- --all 2>&1 || pytest -v 2>&1)",
                path
            ),
            TaskType::TestFile => format!(
                "cd {} && (cargo test --test {} 2>&1 || npm test {} 2>&1 || pytest {} 2>&1)",
                path, path, path, path
            ),
            TaskType::TestFunction => format!(
                "cd {} && (cargo test {} 2>&1 || npm test -- -t '{}' 2>&1 || pytest -k '{}' 2>&1)",
                path, search, search, search
            ),
            TaskType::TestWatch => format!(
                "cd {} && (cargo watch -x test 2>&1 || npm test -- --watch 2>&1 || pytest-watch 2>&1)",
                path
            ),
            TaskType::TestCoverage => format!(
                "cd {} && (cargo tarpaulin 2>&1 || npm test -- --coverage 2>&1 || pytest --cov 2>&1)",
                path
            ),
            TaskType::TestSnapshot => format!("cd {} && npm test -- -u 2>&1", path),
            TaskType::TestUpdate => format!("cd {} && npm test -- --updateSnapshot 2>&1", path),
            TaskType::Benchmark => format!("cd {} && cargo bench 2>&1 || npm run bench 2>&1", path),

            // DEPENDENCIES
            TaskType::Install => format!(
                "cd {} && (npm install '{}' 2>&1 || pip install '{}' 2>&1 || cargo add '{}' 2>&1 || echo 'Install failed')",
                path, search, search, search
            ),
            TaskType::InstallDev => format!(
                "cd {} && (npm install -D '{}' 2>&1 || pip install --dev '{}' 2>&1)",
                path, search, search
            ),
            TaskType::Uninstall => format!(
                "cd {} && (npm uninstall '{}' 2>&1 || pip uninstall '{}' 2>&1 || cargo remove '{}' 2>&1)",
                path, search, search, search
            ),
            TaskType::Update => format!(
                "cd {} && (npm update 2>&1 || pip install --upgrade -r requirements.txt 2>&1 || cargo update 2>&1)",
                path
            ),
            TaskType::UpdateAll => format!(
                "cd {} && (npm update 2>&1 && cargo update 2>&1 || echo 'Update complete')",
                path
            ),
            TaskType::Outdated => format!(
                "cd {} && (npm outdated 2>&1 || pip list --outdated 2>&1 || cargo outdated 2>&1)",
                path
            ),
            TaskType::Audit => format!("cd {} && npm audit 2>&1 || cargo audit 2>&1", path),
            TaskType::AuditFix => format!("cd {} && npm audit fix 2>&1", path),
            TaskType::Lock => format!("cd {} && npm ci 2>&1 || cargo generate-lockfile 2>&1", path),

            // PROCESSES & PORTS
            TaskType::ProcessList => "ps aux | head -50".to_string(),
            TaskType::ProcessFind => format!("ps aux | grep -i '{}' | head -20", search),
            TaskType::ProcessKill => {
                if let Some(pid) = entities.numbers.first() {
                    format!("kill {}", pid)
                } else {
                    format!("pkill -f '{}'", search)
                }
            }
            TaskType::ProcessKillByName => format!("pkill -f '{}'", search),
            TaskType::ProcessKillByPort => format!("lsof -ti:{} | xargs kill -9 2>/dev/null || echo 'No process on port {}'", port, port),
            TaskType::PortList => "lsof -i -P | grep LISTEN | head -30".to_string(),
            TaskType::PortFind => format!("lsof -i:{}", port),
            TaskType::PortKill => format!("lsof -ti:{} | xargs kill -9 2>/dev/null || echo 'No process on port {}'", port, port),

            // SYSTEM
            TaskType::SystemInfo => "uname -a && sw_vers 2>/dev/null || cat /etc/os-release 2>/dev/null".to_string(),
            TaskType::DiskUsage => format!("du -sh {} 2>/dev/null || du -sh .", path),
            TaskType::DiskFree => "df -h".to_string(),
            TaskType::MemoryUsage => "vm_stat 2>/dev/null || free -h 2>/dev/null || echo 'Memory info not available'".to_string(),
            TaskType::CpuUsage => "top -l 1 | head -10 2>/dev/null || uptime".to_string(),
            TaskType::NetworkInfo => "ifconfig 2>/dev/null || ip addr".to_string(),
            TaskType::EnvList => "env | sort | head -50".to_string(),
            TaskType::EnvGet => format!("echo ${}", search),
            TaskType::EnvSet => return None, // Dangerous, don't allow
            TaskType::PathList => "echo $PATH | tr ':' '\\n'".to_string(),
            TaskType::WhichCommand => format!("which '{}'", search),

            // DOCKER
            TaskType::DockerPs => "docker ps".to_string(),
            TaskType::DockerImages => "docker images".to_string(),
            TaskType::DockerBuild => format!("docker build -t {} {}", search, path),
            TaskType::DockerRun => format!("docker run {}", search),
            TaskType::DockerStop => format!("docker stop {}", search),
            TaskType::DockerRm => format!("docker rm {}", search),
            TaskType::DockerLogs => format!("docker logs {} --tail 100", search),
            TaskType::DockerExec => format!("docker exec -it {} /bin/sh", search),
            TaskType::DockerCompose => format!("cd {} && docker-compose up -d", path),
            TaskType::DockerPrune => "docker system prune -af".to_string(),

            // DATABASE (basic)
            TaskType::DbConnect => return None,
            TaskType::DbQuery => return None,
            TaskType::DbList => return None,
            TaskType::DbCreate => return None,
            TaskType::DbDrop => return None,
            TaskType::DbMigrate => format!("cd {} && (npx prisma migrate dev 2>&1 || python manage.py migrate 2>&1)", path),
            TaskType::DbSeed => format!("cd {} && (npx prisma db seed 2>&1 || python manage.py loaddata 2>&1)", path),
            TaskType::DbBackup => return None,
            TaskType::DbRestore => return None,

            // HTTP/CURL
            TaskType::HttpGet => {
                if let Some(url) = entities.urls.first() {
                    format!("curl -s '{}'", url)
                } else {
                    return None;
                }
            }
            TaskType::HttpPost => {
                if let Some(url) = entities.urls.first() {
                    format!("curl -X POST '{}'", url)
                } else {
                    return None;
                }
            }
            TaskType::HttpPut => return None,
            TaskType::HttpDelete => return None,
            TaskType::ApiTest => return None,
            TaskType::CurlRequest => {
                if let Some(url) = entities.urls.first() {
                    format!("curl -v '{}'", url)
                } else {
                    return None;
                }
            }

            // PACKAGE MANAGERS
            TaskType::YarnInstall => "yarn install".to_string(),
            TaskType::YarnAdd => format!("yarn add {}", search),
            TaskType::YarnRemove => format!("yarn remove {}", search),
            TaskType::YarnUpgrade => "yarn upgrade".to_string(),
            TaskType::YarnDev => "yarn dev".to_string(),
            TaskType::YarnBuild => "yarn build".to_string(),
            TaskType::YarnStart => "yarn start".to_string(),
            TaskType::PnpmInstall => "pnpm install".to_string(),
            TaskType::PnpmAdd => format!("pnpm add {}", search),
            TaskType::PnpmRemove => format!("pnpm remove {}", search),
            TaskType::PoetryInstall => "poetry install".to_string(),
            TaskType::PoetryAdd => format!("poetry add {}", search),
            TaskType::PoetryRemove => format!("poetry remove {}", search),
            TaskType::PoetryUpdate => "poetry update".to_string(),
            TaskType::PipenvInstall => "pipenv install".to_string(),
            TaskType::PipenvLock => "pipenv lock".to_string(),
            TaskType::BunInstall => "bun install".to_string(),
            TaskType::BunAdd => format!("bun add {}", search),
            TaskType::BunRun => format!("bun run {}", search),

            // CLOUD/DEVOPS
            TaskType::AwsCli => "aws --version".to_string(),
            TaskType::AwsS3Ls => format!("aws s3 ls {}", if path != "." { path } else { "" }),
            TaskType::AwsS3Cp => format!("aws s3 cp {} {}", path, entities.paths.get(1).unwrap_or(&".".to_string())),
            TaskType::AwsS3Sync => format!("aws s3 sync {} {}", path, entities.paths.get(1).unwrap_or(&".".to_string())),
            TaskType::AwsEc2List => "aws ec2 describe-instances --query 'Reservations[].Instances[].{ID:InstanceId,State:State.Name,Type:InstanceType}'".to_string(),
            TaskType::AwsLambdaList => "aws lambda list-functions".to_string(),
            TaskType::AwsLambdaInvoke => format!("aws lambda invoke --function-name {} /dev/stdout", search),
            TaskType::GcloudList => "gcloud projects list".to_string(),
            TaskType::GcloudDeploy => "gcloud app deploy".to_string(),
            TaskType::AzureCli => "az --version".to_string(),
            TaskType::KubectlGet => format!("kubectl get {}", if search.is_empty() { "pods" } else { search }),
            TaskType::KubectlDescribe => format!("kubectl describe {}", search),
            TaskType::KubectlLogs => format!("kubectl logs {} --tail=100", search),
            TaskType::KubectlApply => format!("kubectl apply -f {}", path),
            TaskType::KubectlDelete => format!("kubectl delete {}", search),
            TaskType::KubectlExec => format!("kubectl exec -it {} -- /bin/sh", search),
            TaskType::KubectlPortForward => format!("kubectl port-forward {} {}", search, port),
            TaskType::HelmInstall => format!("helm install {} {}", search, path),
            TaskType::HelmUpgrade => format!("helm upgrade {} {}", search, path),
            TaskType::HelmList => "helm list".to_string(),
            TaskType::HelmUninstall => format!("helm uninstall {}", search),
            TaskType::TerraformInit => "terraform init".to_string(),
            TaskType::TerraformPlan => "terraform plan".to_string(),
            TaskType::TerraformApply => "terraform apply -auto-approve".to_string(),
            TaskType::TerraformDestroy => "terraform destroy".to_string(),
            TaskType::AnsiblePlaybook => format!("ansible-playbook {}", path),
            TaskType::AnsibleInventory => "ansible-inventory --list".to_string(),

            // ADVANCED GIT
            TaskType::GitBisect => "git bisect".to_string(),
            TaskType::GitBisectStart => "git bisect start".to_string(),
            TaskType::GitBisectGood => "git bisect good".to_string(),
            TaskType::GitBisectBad => "git bisect bad".to_string(),
            TaskType::GitBisectReset => "git bisect reset".to_string(),
            TaskType::GitWorktree => "git worktree list".to_string(),
            TaskType::GitWorktreeAdd => format!("git worktree add {} {}", path, branch),
            TaskType::GitWorktreeList => "git worktree list".to_string(),
            TaskType::GitReflog => "git reflog -30".to_string(),
            TaskType::GitFsck => "git fsck".to_string(),
            TaskType::GitSubmodule => "git submodule status".to_string(),
            TaskType::GitSubmoduleUpdate => "git submodule update --init --recursive".to_string(),
            TaskType::GitLfs => "git lfs status".to_string(),
            TaskType::GitLfsPull => "git lfs pull".to_string(),
            TaskType::GitLfsPush => "git lfs push --all origin".to_string(),
            TaskType::GitArchive => format!("git archive --format=zip HEAD -o {}.zip", branch),
            TaskType::GitBundle => format!("git bundle create {}.bundle --all", branch),
            TaskType::GitShortlog => "git shortlog -sn".to_string(),
            TaskType::GitDescribe => "git describe --tags --always".to_string(),
            TaskType::GitNotes => "git notes list".to_string(),

            // DEBUGGING/PROFILING
            TaskType::LldbRun => format!("lldb {}", path),
            TaskType::LldbAttach => format!("lldb -p {}", entities.numbers.first().unwrap_or(&0)),
            TaskType::GdbRun => format!("gdb {}", path),
            TaskType::GdbAttach => format!("gdb -p {}", entities.numbers.first().unwrap_or(&0)),
            TaskType::Valgrind => format!("valgrind --leak-check=full {}", path),
            TaskType::Strace => format!("strace {}", path),
            TaskType::Dtrace => format!("dtrace -n 'syscall:::entry {{ @[execname] = count(); }}'"),
            TaskType::PerfRecord => format!("perf record {}", path),
            TaskType::PerfReport => "perf report".to_string(),
            TaskType::Flamegraph => format!("cargo flamegraph -- {}", path),
            TaskType::HeapProfile => format!("heaptrack {}", path),
            TaskType::CpuProfile => "instruments -t 'Time Profiler'".to_string(),
            TaskType::MemoryProfile => "instruments -t 'Allocations'".to_string(),

            // SECURITY SCANNING
            TaskType::TrivyScan => format!("trivy fs {}", path),
            TaskType::SnykTest => format!("cd {} && snyk test", path),
            TaskType::BanditScan => format!("bandit -r {}", path),
            TaskType::SafetyCheck => "safety check".to_string(),
            TaskType::NpmAuditFix => "npm audit fix".to_string(),
            TaskType::CargoAuditFix => "cargo audit fix".to_string(),
            TaskType::OsvScanner => format!("osv-scanner {}", path),
            TaskType::GitleaksScan => format!("gitleaks detect --source {}", path),
            TaskType::SemgrepScan => format!("semgrep --config auto {}", path),

            // DOCUMENTATION
            TaskType::Rustdoc => "cargo doc --open".to_string(),
            TaskType::Jsdoc => format!("jsdoc {}", path),
            TaskType::Typedoc => format!("typedoc {}", path),
            TaskType::Sphinx => format!("cd {} && make html", path),
            TaskType::Mkdocs => format!("cd {} && mkdocs serve", path),
            TaskType::Docusaurus => format!("cd {} && npm run start", path),
            TaskType::Storybook => format!("cd {} && npm run storybook", path),

            // DATABASE CLI
            TaskType::PsqlConnect => format!("psql {}", if !search.is_empty() { search } else { "" }),
            TaskType::PsqlQuery => format!("psql -c '{}'", search),
            TaskType::PsqlList => "psql -l".to_string(),
            TaskType::MysqlConnect => format!("mysql {}", if !search.is_empty() { format!("-D {}", search) } else { "".to_string() }),
            TaskType::MysqlQuery => format!("mysql -e '{}'", search),
            TaskType::MysqlList => "mysql -e 'SHOW DATABASES'".to_string(),
            TaskType::SqliteQuery => format!("sqlite3 {} '{}'", path, search),
            TaskType::SqliteList => format!("sqlite3 {} '.tables'", path),
            TaskType::RedisConnect => "redis-cli".to_string(),
            TaskType::RedisCli => "redis-cli".to_string(),
            TaskType::RedisGet => format!("redis-cli GET {}", search),
            TaskType::RedisSet => format!("redis-cli SET {} '{}'", search, message),
            TaskType::RedisKeys => format!("redis-cli KEYS '{}'", if !search.is_empty() { search } else { "*" }),
            TaskType::MongoConnect => "mongosh".to_string(),
            TaskType::MongoshQuery => format!("mongosh --eval '{}'", search),
            TaskType::MongoList => "mongosh --eval 'show dbs'".to_string(),

            // TMUX/SCREEN
            TaskType::TmuxNew => format!("tmux new -s {}", if !search.is_empty() { search } else { "main" }),
            TaskType::TmuxList => "tmux ls".to_string(),
            TaskType::TmuxAttach => format!("tmux attach -t {}", if !search.is_empty() { search } else { "0" }),
            TaskType::TmuxKill => format!("tmux kill-session -t {}", search),
            TaskType::TmuxSplit => "tmux split-window".to_string(),
            TaskType::TmuxSend => format!("tmux send-keys '{}' Enter", search),
            TaskType::ScreenNew => format!("screen -S {}", if !search.is_empty() { search } else { "main" }),
            TaskType::ScreenList => "screen -ls".to_string(),
            TaskType::ScreenAttach => format!("screen -r {}", search),

            // SSH/REMOTE
            TaskType::SshConnect => format!("ssh {}", search),
            TaskType::SshCopy => format!("ssh-copy-id {}", search),
            TaskType::SshTunnel => format!("ssh -L {}:localhost:{} {}", port, port, search),
            TaskType::ScpCopy => {
                if entities.paths.len() >= 2 {
                    format!("scp {} {}", entities.paths[0], entities.paths[1])
                } else {
                    return None;
                }
            }
            TaskType::RsyncSync => {
                if entities.paths.len() >= 2 {
                    format!("rsync -avz {} {}", entities.paths[0], entities.paths[1])
                } else {
                    return None;
                }
            }
            TaskType::SftpConnect => format!("sftp {}", search),

            // LOG ANALYSIS
            TaskType::TailFollow => format!("tail -f {}", path),
            TaskType::TailLines => format!("tail -n {} {}", entities.numbers.first().unwrap_or(&100), path),
            TaskType::Journalctl => format!("journalctl -u {} --no-pager | tail -100", search),
            TaskType::JournalctlFollow => format!("journalctl -u {} -f", search),
            TaskType::LogGrep => format!("grep -i '{}' {} | tail -100", search, path),
            TaskType::LogParse => format!("cat {} | awk '{{print $1, $2, $3}}'", path),
            TaskType::AwsLogs => format!("aws logs tail {} --follow", search),

            // FRAMEWORK SPECIFIC
            TaskType::DjangoManage => format!("python manage.py {}", search),
            TaskType::DjangoMigrate => "python manage.py migrate".to_string(),
            TaskType::DjangoShell => "python manage.py shell".to_string(),
            TaskType::DjangoTest => "python manage.py test".to_string(),
            TaskType::RailsConsole => "rails console".to_string(),
            TaskType::RailsServer => "rails server".to_string(),
            TaskType::RailsMigrate => "rake db:migrate".to_string(),
            TaskType::RailsGenerate => format!("rails generate {}", search),
            TaskType::NextDev => "npx next dev".to_string(),
            TaskType::NextBuild => "npx next build".to_string(),
            TaskType::NextStart => "npx next start".to_string(),
            TaskType::NuxtDev => "npx nuxt dev".to_string(),
            TaskType::NuxtBuild => "npx nuxt build".to_string(),
            TaskType::ViteDev => "npx vite".to_string(),
            TaskType::ViteBuild => "npx vite build".to_string(),
            TaskType::CreateReactApp => format!("npx create-react-app {}", search),
            TaskType::AngularServe => "ng serve".to_string(),
            TaskType::AngularBuild => "ng build".to_string(),
            TaskType::FlutterRun => "flutter run".to_string(),
            TaskType::FlutterBuild => "flutter build".to_string(),
            TaskType::ExpoStart => "npx expo start".to_string(),
            TaskType::ReactNativeStart => "npx react-native start".to_string(),

            // COMPOUND COMMANDS
            TaskType::CommitAndPush => format!("git add -A && git commit -m '{}' && git push", message),
            TaskType::BuildAndTest => format!("cd {} && (cargo build && cargo test || npm run build && npm test)", path),
            TaskType::BuildAndRun => format!("cd {} && (cargo build && cargo run || npm run build && npm start)", path),
            TaskType::PullAndBuild => format!("cd {} && git pull && (cargo build || npm run build)", path),
            TaskType::CleanAndBuild => format!("cd {} && (cargo clean && cargo build || rm -rf node_modules && npm install && npm run build)", path),
            TaskType::TestAndCoverage => format!("cd {} && (cargo tarpaulin || npm test -- --coverage)", path),
            TaskType::LintAndFix => format!("cd {} && (cargo clippy --fix || eslint . --fix)", path),
            TaskType::FormatAndCommit => format!("cd {} && (cargo fmt || npx prettier --write .) && git add -A && git commit -m 'Format code'", path),

            // CONTEXT-AWARE (need runtime state, return helpful message)
            TaskType::RunAgain => "echo 'Use !! in your shell to repeat the last command'".to_string(),
            TaskType::Undo => "git checkout -- . 2>/dev/null || echo 'Nothing to undo'".to_string(),
            TaskType::Retry => "echo 'Use !! in your shell to retry the last command'".to_string(),
            TaskType::LastCommand => "history | tail -1".to_string(),
            TaskType::EditLastFile => "echo 'Last file tracking not implemented yet'".to_string(),
            TaskType::CdBack => "cd -".to_string(),
            TaskType::CdPrevious => "cd ..".to_string(),

            // MISC
            TaskType::Help => "echo 'SAM Intelligence Engine v3 - 250+ task types. Try: git status, find *.rs, kubectl get pods, yarn dev, etc.'".to_string(),
            TaskType::Version => "echo 'SAM Intelligence Engine v3.0 - Comprehensive Coverage'".to_string(),
            TaskType::Clear => "clear".to_string(),
            TaskType::History => "history | tail -50".to_string(),
            TaskType::Alias => "alias".to_string(),
            TaskType::Time => "date '+%H:%M:%S'".to_string(),
            TaskType::Date => "date '+%Y-%m-%d'".to_string(),
            TaskType::Calendar => "cal".to_string(),
            TaskType::Calculator => {
                if let Some(expr) = entities.quoted.first() {
                    format!("echo '{}' | bc -l", expr)
                } else {
                    return None;
                }
            }
            TaskType::Uuid => "uuidgen".to_string(),
            TaskType::Base64Encode => format!("echo '{}' | base64", search),
            TaskType::Base64Decode => format!("echo '{}' | base64 -d", search),
            TaskType::Md5Sum => format!("md5 {} 2>/dev/null || md5sum {}", path, path),
            TaskType::Sha256Sum => format!("shasum -a 256 {}", path),
            TaskType::JsonFormat => format!("cat {} | jq '.'", path),
            TaskType::JsonValidate => format!("cat {} | jq empty && echo 'Valid JSON'", path),
            TaskType::XmlFormat => format!("xmllint --format {}", path),
            TaskType::YamlToJson => format!("cat {} | python3 -c 'import sys,yaml,json; print(json.dumps(yaml.safe_load(sys.stdin), indent=2))'", path),
            TaskType::JsonToYaml => format!("cat {} | python3 -c 'import sys,yaml,json; print(yaml.dump(json.load(sys.stdin)))'", path),
            TaskType::UrlEncode => format!("python3 -c \"import urllib.parse; print(urllib.parse.quote('{}'))\"", search),
            TaskType::UrlDecode => format!("python3 -c \"import urllib.parse; print(urllib.parse.unquote('{}'))\"", search),
            TaskType::Hostname => "hostname".to_string(),
            TaskType::Whoami => "whoami".to_string(),
            TaskType::Uptime => "uptime".to_string(),

            // NETWORK
            TaskType::Ping => format!("ping -c 4 {}", search),
            TaskType::Traceroute => format!("traceroute {}", search),
            TaskType::Dig => format!("dig {}", search),
            TaskType::Nslookup => format!("nslookup {}", search),
            TaskType::Netstat => "netstat -an | head -50".to_string(),
            TaskType::Ss => "ss -tuln".to_string(),
            TaskType::Ifconfig => "ifconfig".to_string(),
            TaskType::IpAddr => "ip addr 2>/dev/null || ifconfig".to_string(),
            TaskType::Arp => "arp -a".to_string(),
            TaskType::Nmap => format!("nmap {}", search),
            TaskType::Tcpdump => format!("tcpdump -i any -c 100 host {}", search),

            // MEDIA/FILES
            TaskType::ImageInfo => format!("file {} && sips -g all {} 2>/dev/null || identify {}", path, path, path),
            TaskType::ImageResize => format!("sips -Z {} {} 2>/dev/null || convert {} -resize {} {}", entities.numbers.first().unwrap_or(&800), path, path, entities.numbers.first().unwrap_or(&800), path),
            TaskType::ImageConvert => format!("sips -s format {} {} 2>/dev/null || convert {} {}", search, path, path, search),
            TaskType::VideoInfo => format!("ffprobe -v quiet -print_format json -show_format -show_streams {}", path),
            TaskType::AudioInfo => format!("ffprobe -v quiet -print_format json -show_format {}", path),
            TaskType::PdfInfo => format!("pdfinfo {} 2>/dev/null || mdls {}", path, path),
            TaskType::PdfMerge => {
                if entities.paths.len() >= 2 {
                    format!("pdfunite {} output.pdf", entities.paths.join(" "))
                } else {
                    return None;
                }
            }
            TaskType::PdfSplit => format!("pdfseparate {} {}/page-%d.pdf", path, path),

            // HTTP extras
            TaskType::HttpHead => {
                if let Some(url) = entities.urls.first() {
                    format!("curl -I '{}'", url)
                } else {
                    return None;
                }
            }
            TaskType::HttpOptions => {
                if let Some(url) = entities.urls.first() {
                    format!("curl -X OPTIONS -I '{}'", url)
                } else {
                    return None;
                }
            }
            TaskType::HttpPatch => {
                if let Some(url) = entities.urls.first() {
                    format!("curl -X PATCH '{}'", url)
                } else {
                    return None;
                }
            }

            // SHELL - execute raw command
            TaskType::Shell => raw_input.trim_start_matches('$').trim().to_string(),

            // CATCH-ALL
            _ => return None,
        };

        Some(cmd)
    }
}

// =============================================================================
// MAIN ENGINE V2
// =============================================================================

pub struct IntelligenceEngineV2 {
    keywords: KeywordDatabase,
    extractor: SmartExtractor,
}

impl IntelligenceEngineV2 {
    pub fn new() -> Self {
        Self {
            keywords: KeywordDatabase::new(),
            extractor: SmartExtractor::new(),
        }
    }

    pub fn process(&self, input: &str) -> ProcessedRequest {
        let (task_type, confidence) = self.keywords.classify(input);
        let entities = self.extractor.extract_all(input);
        let command = WorkflowEngineV2::get_command(task_type, &entities, input);

        ProcessedRequest {
            input: input.to_string(),
            task_type,
            confidence,
            entities,
            command,
        }
    }

    pub fn execute(&self, input: &str) -> ExecutionResult {
        let processed = self.process(input);

        if processed.confidence < 0.05 {
            return ExecutionResult {
                success: false,
                task_type: processed.task_type,
                command: None,
                output: format!("Could not understand: '{}'. Try being more specific.", input),
                time_ms: 0,
            };
        }

        let command = match &processed.command {
            Some(cmd) => cmd.clone(),
            None => {
                return ExecutionResult {
                    success: false,
                    task_type: processed.task_type,
                    command: None,
                    output: format!("No command available for task type: {:?}", processed.task_type),
                    time_ms: 0,
                };
            }
        };

        let start = std::time::Instant::now();

        let result = Command::new("sh")
            .arg("-c")
            .arg(&command)
            .output();

        let time_ms = start.elapsed().as_millis() as u64;

        match result {
            Ok(output) => {
                let stdout = String::from_utf8_lossy(&output.stdout);
                let stderr = String::from_utf8_lossy(&output.stderr);

                let combined = if stderr.is_empty() || output.status.success() {
                    stdout.to_string()
                } else {
                    format!("{}\n{}", stdout, stderr)
                };

                ExecutionResult {
                    success: output.status.success(),
                    task_type: processed.task_type,
                    command: Some(command),
                    output: combined,
                    time_ms,
                }
            }
            Err(e) => ExecutionResult {
                success: false,
                task_type: processed.task_type,
                command: Some(command),
                output: format!("Execution failed: {}", e),
                time_ms,
            },
        }
    }
}

#[derive(Debug)]
pub struct ProcessedRequest {
    pub input: String,
    pub task_type: TaskType,
    pub confidence: f32,
    pub entities: ExtractedEntities,
    pub command: Option<String>,
}

#[derive(Debug, Serialize)]
pub struct ExecutionResult {
    pub success: bool,
    pub task_type: TaskType,
    pub command: Option<String>,
    pub output: String,
    pub time_ms: u64,
}

// =============================================================================
// TESTS
// =============================================================================

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_classification() {
        let db = KeywordDatabase::new();

        // Git commands
        assert_eq!(db.classify("git status").0, TaskType::GitStatus);
        assert_eq!(db.classify("git diff").0, TaskType::GitDiff);
        assert_eq!(db.classify("git log").0, TaskType::GitLog);

        // File operations
        assert_eq!(db.classify("find all *.py files").0, TaskType::FindFiles);
        assert_eq!(db.classify("ls").0, TaskType::ListDirectory);

        // Code search
        assert_eq!(db.classify("find function main").0, TaskType::SearchFunction);
        assert_eq!(db.classify("grep for error").0, TaskType::SearchText);
    }

    #[test]
    fn test_extraction() {
        let extractor = SmartExtractor::new();

        let entities = extractor.extract_all("find all *.py files in /tmp/project");
        assert!(entities.paths.contains(&"/tmp/project".to_string()));
        assert_eq!(entities.glob, Some("*.py".to_string()));

        let entities = extractor.extract_all("search for 'hello world'");
        assert_eq!(entities.search_term, Some("hello world".to_string()));
    }

    #[test]
    fn test_full_pipeline() {
        let engine = IntelligenceEngineV2::new();

        let result = engine.process("git status");
        assert_eq!(result.task_type, TaskType::GitStatus);
        assert_eq!(result.command, Some("git status".to_string()));

        let result = engine.process("find all *.rs files in ~/Projects");
        assert_eq!(result.task_type, TaskType::FindFiles);
        assert!(result.command.is_some());
    }
}
