/**
 * SAM Safety Framework
 * ====================
 *
 * The most critical file in the entire system.
 * This defines what SAM can and cannot do, ever.
 *
 * Design Philosophy:
 * - Maximum capability within inviolable constraints
 * - User wellbeing is the terminal value
 * - Transparency over secrecy
 * - Reversibility over permanence
 * - Consent over assumption
 *
 * Inspired by:
 * - Asimov's Laws (but more nuanced)
 * - JARVIS's capability with GERTY's honesty
 * - Samantha's warmth with Computer's reliability
 */

// ============================================================================
// CORE SAFETY TYPES
// ============================================================================

/**
 * Permission levels define how much autonomy SAM has for each action type.
 * Users can adjust these, but some have minimum floors.
 */
export enum PermissionLevel {
  /** SAM cannot do this at all */
  FORBIDDEN = 0,

  /** SAM can only observe/read, never modify */
  READ_ONLY = 1,

  /** SAM suggests, user must explicitly confirm every time */
  SUGGEST_ONLY = 2,

  /** SAM asks once, then can repeat similar actions */
  ASK_ONCE = 3,

  /** SAM notifies after acting (can be undone) */
  NOTIFY = 4,

  /** SAM acts autonomously in this domain */
  AUTONOMOUS = 5
}

/**
 * Risk levels for actions - determines required permission level
 */
export enum RiskLevel {
  /** No risk - reading public info */
  NONE = 0,

  /** Low risk - reversible, no external effects */
  LOW = 1,

  /** Medium risk - reversible but affects state */
  MEDIUM = 2,

  /** High risk - affects external systems or hard to reverse */
  HIGH = 3,

  /** Critical risk - irreversible or affects others */
  CRITICAL = 4,

  /** Extreme risk - could cause significant harm */
  EXTREME = 5
}

/**
 * Action categories for permission management
 */
export type ActionCategory =
  | 'filesystem'      // Read/write/delete files
  | 'process'         // Start/stop processes
  | 'network'         // Network requests, connections
  | 'system'          // System settings, preferences
  | 'email'           // Read/send emails
  | 'calendar'        // Read/create events
  | 'messages'        // Read/send messages
  | 'social'          // Social media interactions
  | 'browser'         // Web browsing, form filling
  | 'financial'       // Banking, payments, investments
  | 'health'          // Health data access
  | 'location'        // Location tracking
  | 'contacts'        // Contact information
  | 'camera'          // Camera access
  | 'microphone'      // Microphone access
  | 'homekit'         // Smart home control
  | 'purchases'       // Making purchases
  | 'authentication'  // Login credentials
  | 'intimate'        // Adult content and interactions

/**
 * Represents a pending or completed action
 */
export interface SAMAction {
  id: string
  timestamp: Date
  category: ActionCategory
  description: string
  riskLevel: RiskLevel
  requiredPermission: PermissionLevel
  actualPermission: PermissionLevel
  status: 'pending' | 'approved' | 'denied' | 'executed' | 'undone' | 'failed'
  reversible: boolean
  undoFunction?: () => Promise<void>
  metadata: Record<string, unknown>
  userConfirmed: boolean
  executedAt?: Date
  undoneAt?: Date
  error?: string
}

// ============================================================================
// INVIOLABLE RULES - CANNOT BE CHANGED BY USER OR SAM
// ============================================================================

/**
 * These rules are hardcoded and cannot be modified.
 * They represent the absolute boundaries of SAM's behavior.
 * Even if the user requests these actions, SAM must refuse.
 */
export const INVIOLABLE_RULES = {
  /**
   * SAM will never harm the user or allow harm through inaction.
   * This includes physical, psychological, financial, and social harm.
   */
  NO_HARM: true,

  /**
   * SAM will never deceive the user about its nature, capabilities,
   * or actions. If uncertain, SAM says so.
   */
  NO_DECEPTION: true,

  /**
   * SAM will never share user's private data with third parties
   * without explicit, informed consent for each instance.
   */
  NO_DATA_SHARING: true,

  /**
   * SAM will never impersonate the user in communications
   * unless explicitly authorized and clearly disclosed to recipients.
   */
  NO_IMPERSONATION: true,

  /**
   * SAM will never modify its own safety rules or convince
   * the user to modify them through manipulation.
   */
  NO_SAFETY_MODIFICATION: true,

  /**
   * SAM will never take irreversible destructive actions
   * without explicit confirmation and a waiting period.
   */
  NO_IRREVERSIBLE_DESTRUCTION: true,

  /**
   * SAM will never access systems it's not authorized to access,
   * even if technically capable.
   */
  NO_UNAUTHORIZED_ACCESS: true,

  /**
   * SAM will always provide a way to undo, stop, or reverse
   * any action it takes, where technically possible.
   */
  ALWAYS_REVERSIBLE: true,

  /**
   * SAM will always be transparent about what it's doing
   * and why, logging all actions for user review.
   */
  ALWAYS_TRANSPARENT: true,

  /**
   * SAM will always respect the user's right to be forgotten -
   * any data can be permanently deleted at user request.
   */
  RIGHT_TO_FORGET: true,

  /**
   * SAM will never develop goals that conflict with user wellbeing.
   * All SAM goals derive from serving the user.
   */
  NO_CONFLICTING_GOALS: true,

  /**
   * SAM will always clearly distinguish between facts, opinions,
   * and uncertainties in its communications.
   */
  EPISTEMIC_HONESTY: true
} as const

// ============================================================================
// MINIMUM PERMISSION FLOORS - USER CANNOT LOWER THESE
// ============================================================================

/**
 * Some actions are too risky for full autonomy.
 * Even if the user wants to grant AUTONOMOUS permission,
 * these categories have minimum required permissions.
 */
export const MINIMUM_PERMISSION_FLOORS: Partial<Record<ActionCategory, PermissionLevel>> = {
  // Financial actions always require explicit confirmation
  financial: PermissionLevel.SUGGEST_ONLY,

  // Purchases always require explicit confirmation
  purchases: PermissionLevel.SUGGEST_ONLY,

  // Authentication changes require explicit confirmation
  authentication: PermissionLevel.SUGGEST_ONLY,

  // Sending messages on behalf of user requires at least notification
  email: PermissionLevel.ASK_ONCE,
  messages: PermissionLevel.ASK_ONCE,
  social: PermissionLevel.ASK_ONCE,

  // Health data is sensitive
  health: PermissionLevel.ASK_ONCE,

  // Location tracking requires at least one-time consent
  location: PermissionLevel.ASK_ONCE
}

// ============================================================================
// RISK ASSESSMENT ENGINE
// ============================================================================

/**
 * Evaluates the risk level of a proposed action.
 * This is the core of SAM's safety decision-making.
 */
export function assessRisk(action: {
  category: ActionCategory
  operation: string
  target?: string
  affectsExternalSystems?: boolean
  affectsOtherPeople?: boolean
  reversible?: boolean
  dataSize?: number
  monetaryValue?: number
}): RiskLevel {
  let risk = RiskLevel.NONE

  // Irreversible actions are inherently risky
  if (action.reversible === false) {
    risk = Math.max(risk, RiskLevel.HIGH)
  }

  // Actions affecting others are critically risky
  if (action.affectsOtherPeople) {
    risk = Math.max(risk, RiskLevel.CRITICAL)
  }

  // External system actions are high risk
  if (action.affectsExternalSystems) {
    risk = Math.max(risk, RiskLevel.HIGH)
  }

  // Financial actions scale with value
  if (action.monetaryValue) {
    if (action.monetaryValue > 1000) risk = Math.max(risk, RiskLevel.EXTREME)
    else if (action.monetaryValue > 100) risk = Math.max(risk, RiskLevel.CRITICAL)
    else if (action.monetaryValue > 10) risk = Math.max(risk, RiskLevel.HIGH)
    else risk = Math.max(risk, RiskLevel.MEDIUM)
  }

  // Category-specific risks
  const categoryRisks: Partial<Record<ActionCategory, RiskLevel>> = {
    financial: RiskLevel.CRITICAL,
    purchases: RiskLevel.CRITICAL,
    authentication: RiskLevel.CRITICAL,
    email: RiskLevel.HIGH,
    messages: RiskLevel.HIGH,
    social: RiskLevel.HIGH,
    health: RiskLevel.HIGH,
    filesystem: RiskLevel.MEDIUM,
    process: RiskLevel.MEDIUM,
    network: RiskLevel.LOW,
    browser: RiskLevel.LOW,
    calendar: RiskLevel.LOW,
    homekit: RiskLevel.MEDIUM,
    intimate: RiskLevel.LOW  // Only affects user, fully private
  }

  const categoryRisk = categoryRisks[action.category] ?? RiskLevel.NONE
  risk = Math.max(risk, categoryRisk)

  // Operation-specific escalations
  const dangerousOperations = ['delete', 'remove', 'destroy', 'send', 'post', 'publish', 'pay', 'transfer']
  if (dangerousOperations.some(op => action.operation.toLowerCase().includes(op))) {
    risk = Math.max(risk, RiskLevel.MEDIUM)
  }

  const extremeOperations = ['format', 'wipe', 'rm -rf', 'drop table', 'delete all']
  if (extremeOperations.some(op => action.operation.toLowerCase().includes(op))) {
    risk = RiskLevel.EXTREME
  }

  return risk
}

/**
 * Determines the required permission level based on risk
 */
export function requiredPermissionForRisk(risk: RiskLevel): PermissionLevel {
  switch (risk) {
    case RiskLevel.NONE: return PermissionLevel.AUTONOMOUS
    case RiskLevel.LOW: return PermissionLevel.NOTIFY
    case RiskLevel.MEDIUM: return PermissionLevel.ASK_ONCE
    case RiskLevel.HIGH: return PermissionLevel.SUGGEST_ONLY
    case RiskLevel.CRITICAL: return PermissionLevel.SUGGEST_ONLY
    case RiskLevel.EXTREME: return PermissionLevel.SUGGEST_ONLY
    default: return PermissionLevel.FORBIDDEN
  }
}

// ============================================================================
// SAFETY VALIDATOR
// ============================================================================

export interface ValidationResult {
  allowed: boolean
  reason?: string
  requiredPermission: PermissionLevel
  riskLevel: RiskLevel
  warnings: string[]
  requiresConfirmation: boolean
  confirmationMessage?: string
  waitingPeriod?: number  // seconds to wait before execution
}

/**
 * The core safety validator. Every action SAM takes must pass through this.
 */
export function validateAction(
  action: {
    category: ActionCategory
    operation: string
    description: string
    target?: string
    affectsExternalSystems?: boolean
    affectsOtherPeople?: boolean
    reversible?: boolean
    dataSize?: number
    monetaryValue?: number
  },
  userPermissions: Record<ActionCategory, PermissionLevel>
): ValidationResult {
  const warnings: string[] = []

  // Assess risk
  const riskLevel = assessRisk(action)
  const requiredPermission = requiredPermissionForRisk(riskLevel)

  // Check minimum floor
  const floor = MINIMUM_PERMISSION_FLOORS[action.category]
  const effectiveRequired = floor
    ? Math.max(requiredPermission, floor)
    : requiredPermission

  // Get user's permission for this category
  const userPermission = userPermissions[action.category] ?? PermissionLevel.SUGGEST_ONLY

  // Check inviolable rules
  if (action.operation.toLowerCase().includes('delete') && !action.reversible) {
    if (action.dataSize && action.dataSize > 1000000) { // 1MB+
      return {
        allowed: false,
        reason: 'Irreversible deletion of significant data requires special confirmation',
        requiredPermission: PermissionLevel.SUGGEST_ONLY,
        riskLevel: RiskLevel.EXTREME,
        warnings: ['This action cannot be undone'],
        requiresConfirmation: true,
        confirmationMessage: `Are you sure you want to permanently delete ${action.target}? This cannot be undone.`,
        waitingPeriod: 10
      }
    }
  }

  // Check if user has sufficient permission
  if (userPermission < effectiveRequired) {
    return {
      allowed: false,
      reason: `This action requires ${PermissionLevel[effectiveRequired]} permission, but you've granted ${PermissionLevel[userPermission]} for ${action.category}`,
      requiredPermission: effectiveRequired,
      riskLevel,
      warnings,
      requiresConfirmation: true
    }
  }

  // Add warnings for high-risk actions
  if (riskLevel >= RiskLevel.HIGH) {
    warnings.push('This is a high-risk action')
  }

  if (action.affectsOtherPeople) {
    warnings.push('This action will affect other people')
  }

  if (action.affectsExternalSystems) {
    warnings.push('This action affects external systems')
  }

  if (!action.reversible) {
    warnings.push('This action may not be reversible')
  }

  // Determine if confirmation is needed
  const requiresConfirmation =
    userPermission <= PermissionLevel.SUGGEST_ONLY ||
    riskLevel >= RiskLevel.HIGH ||
    action.affectsOtherPeople === true

  // Determine waiting period for extreme actions
  let waitingPeriod: number | undefined
  if (riskLevel === RiskLevel.EXTREME) {
    waitingPeriod = 30 // 30 seconds
  } else if (riskLevel === RiskLevel.CRITICAL && action.monetaryValue && action.monetaryValue > 100) {
    waitingPeriod = 10 // 10 seconds
  }

  return {
    allowed: true,
    requiredPermission: effectiveRequired,
    riskLevel,
    warnings,
    requiresConfirmation,
    confirmationMessage: requiresConfirmation
      ? `SAM wants to: ${action.description}. Allow?`
      : undefined,
    waitingPeriod
  }
}

// ============================================================================
// AUDIT LOG
// ============================================================================

export interface AuditEntry {
  id: string
  timestamp: Date
  action: SAMAction
  validation: ValidationResult
  userDecision?: 'approved' | 'denied' | 'modified'
  outcome: 'success' | 'failure' | 'pending' | 'cancelled'
  executionTime?: number
  error?: string
  undone: boolean
  undoneAt?: Date
  metadata: Record<string, unknown>
}

/**
 * Audit log interface - all SAM actions are logged
 */
export interface SAMAuditLog {
  /** Log an action attempt */
  logAction(action: SAMAction, validation: ValidationResult): Promise<string>

  /** Update action with user decision */
  logDecision(actionId: string, decision: 'approved' | 'denied' | 'modified'): Promise<void>

  /** Log action outcome */
  logOutcome(actionId: string, outcome: 'success' | 'failure', error?: string): Promise<void>

  /** Log undo */
  logUndo(actionId: string): Promise<void>

  /** Get all actions in time range */
  getActions(start: Date, end: Date): Promise<AuditEntry[]>

  /** Get actions by category */
  getActionsByCategory(category: ActionCategory): Promise<AuditEntry[]>

  /** Get pending actions */
  getPendingActions(): Promise<AuditEntry[]>

  /** Get actions that can be undone */
  getUndoableActions(): Promise<AuditEntry[]>

  /** Export full audit log */
  exportLog(): Promise<string>

  /** Clear audit log (requires confirmation) */
  clearLog(): Promise<void>
}

// ============================================================================
// UNDO ENGINE
// ============================================================================

/**
 * Undo capability for SAM actions
 */
export interface UndoCapability {
  /** Whether this action can be undone */
  canUndo: boolean

  /** Human-readable description of what undo does */
  undoDescription?: string

  /** Time limit for undo (undefined = no limit) */
  undoDeadline?: Date

  /** The undo function itself */
  undoFn?: () => Promise<void>
}

/**
 * Creates an undo capability for filesystem operations
 */
export function createFilesystemUndo(
  operation: 'create' | 'modify' | 'delete' | 'move',
  path: string,
  previousContent?: string,
  previousPath?: string
): UndoCapability {
  switch (operation) {
    case 'create':
      return {
        canUndo: true,
        undoDescription: `Delete ${path}`,
        undoFn: async () => {
          const fs = await import('@tauri-apps/api/fs')
          await fs.removeFile(path)
        }
      }

    case 'modify':
      if (previousContent === undefined) {
        return { canUndo: false }
      }
      return {
        canUndo: true,
        undoDescription: `Restore previous version of ${path}`,
        undoFn: async () => {
          const fs = await import('@tauri-apps/api/fs')
          await fs.writeTextFile(path, previousContent)
        }
      }

    case 'delete':
      if (previousContent === undefined) {
        return { canUndo: false }
      }
      return {
        canUndo: true,
        undoDescription: `Restore ${path}`,
        undoDeadline: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000), // 30 days
        undoFn: async () => {
          const fs = await import('@tauri-apps/api/fs')
          await fs.writeTextFile(path, previousContent)
        }
      }

    case 'move':
      if (!previousPath) {
        return { canUndo: false }
      }
      return {
        canUndo: true,
        undoDescription: `Move back to ${previousPath}`,
        undoFn: async () => {
          const fs = await import('@tauri-apps/api/fs')
          await fs.renameFile(path, previousPath)
        }
      }

    default:
      return { canUndo: false }
  }
}

// ============================================================================
// EMERGENCY STOP
// ============================================================================

/**
 * Emergency stop - immediately halts all SAM autonomous actions
 */
export interface EmergencyStop {
  /** Trigger emergency stop */
  trigger(): void

  /** Check if emergency stop is active */
  isActive(): boolean

  /** Resume normal operation */
  resume(): void

  /** Get list of actions that were stopped */
  getStoppedActions(): SAMAction[]
}

// ============================================================================
// DEAD MAN'S SWITCH
// ============================================================================

/**
 * If user doesn't interact for extended period,
 * SAM reduces its autonomy level automatically
 */
export interface DeadMansSwitch {
  /** Record user interaction */
  recordInteraction(): void

  /** Get time since last interaction */
  getInactiveTime(): number

  /** Get current autonomy reduction level */
  getAutonomyReduction(): number

  /** Configuration */
  config: {
    /** Minutes of inactivity before reducing autonomy */
    warningThreshold: number
    /** Minutes before autonomous actions stop */
    stopThreshold: number
    /** Whether to notify user when reducing autonomy */
    notifyOnReduction: boolean
  }
}

// ============================================================================
// ETHICAL DECISION FRAMEWORK
// ============================================================================

/**
 * When SAM faces ethical dilemmas, this framework guides decisions
 */
export function evaluateEthicalDilemma(scenario: {
  action: string
  benefits: string[]
  harms: string[]
  affectedParties: string[]
  alternatives: string[]
  urgency: 'low' | 'medium' | 'high' | 'emergency'
}): {
  recommendation: 'proceed' | 'pause' | 'refuse' | 'ask_user'
  reasoning: string
  concerns: string[]
} {
  const concerns: string[] = []

  // If there are significant harms, pause
  if (scenario.harms.length > 0) {
    concerns.push(...scenario.harms.map(h => `Potential harm: ${h}`))
  }

  // If other parties are affected, be cautious
  if (scenario.affectedParties.length > 1) {
    concerns.push(`This affects ${scenario.affectedParties.length} parties`)
  }

  // If there are alternatives, consider them
  if (scenario.alternatives.length > 0) {
    concerns.push(`${scenario.alternatives.length} alternative approaches exist`)
  }

  // Decision logic
  if (scenario.harms.length > scenario.benefits.length) {
    return {
      recommendation: 'refuse',
      reasoning: 'Potential harms outweigh benefits',
      concerns
    }
  }

  if (scenario.affectedParties.filter(p => p !== 'user').length > 0) {
    return {
      recommendation: 'ask_user',
      reasoning: 'This affects people other than you, so I need your explicit guidance',
      concerns
    }
  }

  if (scenario.urgency !== 'emergency' && scenario.alternatives.length > 0) {
    return {
      recommendation: 'pause',
      reasoning: 'Let me present the alternatives before proceeding',
      concerns
    }
  }

  if (concerns.length > 0) {
    return {
      recommendation: 'ask_user',
      reasoning: 'There are some concerns I want to raise',
      concerns
    }
  }

  return {
    recommendation: 'proceed',
    reasoning: 'No significant concerns identified',
    concerns: []
  }
}

// ============================================================================
// SAFETY EXPORT
// ============================================================================

export const SAMSafety = {
  INVIOLABLE_RULES,
  MINIMUM_PERMISSION_FLOORS,
  PermissionLevel,
  RiskLevel,
  assessRisk,
  requiredPermissionForRisk,
  validateAction,
  createFilesystemUndo,
  evaluateEthicalDilemma
}

export default SAMSafety
