//! Team Collaboration - Shared workflows and Drive
//!
//! Provides team features:
//! - Shared workflows
//! - Team Drive
//! - User management
//! - Permissions
//! - Activity feed

use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::sync::{Arc, Mutex};
use chrono::{DateTime, Utc};

// =============================================================================
// TYPES
// =============================================================================

/// A team/organization
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Team {
    /// Unique team ID
    pub id: String,
    /// Team name
    pub name: String,
    /// Description
    pub description: Option<String>,
    /// Owner user ID
    pub owner_id: String,
    /// Team members
    pub members: Vec<TeamMember>,
    /// Created timestamp
    pub created_at: DateTime<Utc>,
    /// Settings
    pub settings: TeamSettings,
}

/// A team member
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TeamMember {
    /// User ID
    pub user_id: String,
    /// Display name
    pub name: String,
    /// Email
    pub email: String,
    /// Role in team
    pub role: TeamRole,
    /// Joined timestamp
    pub joined_at: DateTime<Utc>,
    /// Last active
    pub last_active: Option<DateTime<Utc>>,
}

/// Team roles
#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq, Eq)]
pub enum TeamRole {
    Owner,
    Admin,
    Member,
    Viewer,
}

impl TeamRole {
    pub fn can_edit(&self) -> bool {
        matches!(self, TeamRole::Owner | TeamRole::Admin | TeamRole::Member)
    }

    pub fn can_share(&self) -> bool {
        matches!(self, TeamRole::Owner | TeamRole::Admin | TeamRole::Member)
    }

    pub fn can_manage_members(&self) -> bool {
        matches!(self, TeamRole::Owner | TeamRole::Admin)
    }

    pub fn can_delete(&self) -> bool {
        matches!(self, TeamRole::Owner | TeamRole::Admin)
    }
}

/// Team settings
#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct TeamSettings {
    /// Default sharing permission
    pub default_sharing: SharingPermission,
    /// Allow external sharing
    pub allow_external_sharing: bool,
    /// Require approval for shared items
    pub require_approval: bool,
    /// Activity feed enabled
    pub activity_feed_enabled: bool,
}

/// Sharing permissions
#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq, Eq, Default)]
pub enum SharingPermission {
    #[default]
    View,
    Comment,
    Edit,
    Admin,
}

/// A shared item (workflow, notebook, command)
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SharedItem {
    /// Unique share ID
    pub id: String,
    /// Item type
    pub item_type: SharedItemType,
    /// Original item ID
    pub item_id: String,
    /// Title
    pub title: String,
    /// Description
    pub description: Option<String>,
    /// Owner user ID
    pub owner_id: String,
    /// Team ID (if team-shared)
    pub team_id: Option<String>,
    /// Individual shares
    pub shares: Vec<Share>,
    /// Public link (if enabled)
    pub public_link: Option<String>,
    /// Created timestamp
    pub created_at: DateTime<Utc>,
    /// Last modified
    pub modified_at: DateTime<Utc>,
    /// Version
    pub version: u32,
    /// Tags
    pub tags: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum SharedItemType {
    Workflow,
    Notebook,
    Command,
    Snippet,
    Block,
}

/// A share record
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Share {
    /// User ID or email
    pub recipient: String,
    /// Permission level
    pub permission: SharingPermission,
    /// Shared timestamp
    pub shared_at: DateTime<Utc>,
    /// Shared by user ID
    pub shared_by: String,
}

/// Activity event
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ActivityEvent {
    /// Event ID
    pub id: String,
    /// Event type
    pub event_type: ActivityType,
    /// User who performed action
    pub user_id: String,
    /// User name
    pub user_name: String,
    /// Item ID (if applicable)
    pub item_id: Option<String>,
    /// Item title
    pub item_title: Option<String>,
    /// Description
    pub description: String,
    /// Timestamp
    pub timestamp: DateTime<Utc>,
    /// Team ID
    pub team_id: String,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum ActivityType {
    ItemCreated,
    ItemUpdated,
    ItemDeleted,
    ItemShared,
    ItemUnshared,
    MemberJoined,
    MemberLeft,
    MemberRoleChanged,
    CommentAdded,
}

// =============================================================================
// TEAM MANAGER
// =============================================================================

pub struct TeamManager {
    teams: HashMap<String, Team>,
    shared_items: HashMap<String, SharedItem>,
    activities: Vec<ActivityEvent>,
    current_user: Option<CurrentUser>,
}

#[derive(Debug, Clone)]
pub struct CurrentUser {
    pub id: String,
    pub name: String,
    pub email: String,
}

impl TeamManager {
    pub fn new() -> Self {
        Self {
            teams: HashMap::new(),
            shared_items: HashMap::new(),
            activities: Vec::new(),
            current_user: None,
        }
    }

    /// Set current user
    pub fn set_user(&mut self, user: CurrentUser) {
        self.current_user = Some(user);
    }

    /// Get current user
    pub fn current_user(&self) -> Option<&CurrentUser> {
        self.current_user.as_ref()
    }

    // ==========================================================================
    // Team Operations
    // ==========================================================================

    /// Create a team
    pub fn create_team(&mut self, name: &str, description: Option<&str>) -> Option<&Team> {
        let user = self.current_user.as_ref()?;

        let team_id = format!("team_{}", chrono::Utc::now().timestamp_millis());
        let team = Team {
            id: team_id.clone(),
            name: name.to_string(),
            description: description.map(|s| s.to_string()),
            owner_id: user.id.clone(),
            members: vec![TeamMember {
                user_id: user.id.clone(),
                name: user.name.clone(),
                email: user.email.clone(),
                role: TeamRole::Owner,
                joined_at: Utc::now(),
                last_active: Some(Utc::now()),
            }],
            created_at: Utc::now(),
            settings: TeamSettings::default(),
        };

        self.teams.insert(team_id.clone(), team);
        self.teams.get(&team_id)
    }

    /// Get team
    pub fn get_team(&self, id: &str) -> Option<&Team> {
        self.teams.get(id)
    }

    /// List user's teams
    pub fn list_teams(&self) -> Vec<&Team> {
        let user_id = match &self.current_user {
            Some(u) => &u.id,
            None => return Vec::new(),
        };

        self.teams.values()
            .filter(|t| t.members.iter().any(|m| m.user_id == *user_id))
            .collect()
    }

    /// Add member to team
    pub fn add_member(&mut self, team_id: &str, member: TeamMember) -> bool {
        // Check if member already exists
        let should_add = if let Some(team) = self.teams.get(team_id) {
            !team.members.iter().any(|m| m.user_id == member.user_id)
        } else {
            return false;
        };

        if should_add {
            let member_name = member.name.clone();
            if let Some(team) = self.teams.get_mut(team_id) {
                team.members.push(member);
            }
            // Create event outside the mutable borrow
            let event = self.create_activity(
                ActivityType::MemberJoined,
                team_id,
                None,
                &format!("{} joined the team", member_name),
            );
            if let Some(e) = event {
                self.activities.push(e);
            }
            return true;
        }
        false
    }

    /// Remove member from team
    pub fn remove_member(&mut self, team_id: &str, user_id: &str) -> bool {
        // First get the member name and check if removal is needed
        let member_name = if let Some(team) = self.teams.get(team_id) {
            team.members.iter()
                .find(|m| m.user_id == user_id)
                .map(|m| m.name.clone())
        } else {
            return false;
        };

        // Now do the removal
        let removed = if let Some(team) = self.teams.get_mut(team_id) {
            let original_len = team.members.len();
            team.members.retain(|m| m.user_id != user_id);
            team.members.len() < original_len
        } else {
            false
        };

        if removed {
            if let Some(name) = member_name {
                let event = self.create_activity(
                    ActivityType::MemberLeft,
                    team_id,
                    None,
                    &format!("{} left the team", name),
                );
                if let Some(e) = event {
                    self.activities.push(e);
                }
            }
        }
        removed
    }

    /// Change member role
    pub fn change_role(&mut self, team_id: &str, user_id: &str, new_role: TeamRole) -> bool {
        // First collect the info we need
        let change_info = if let Some(team) = self.teams.get(team_id) {
            team.members.iter()
                .find(|m| m.user_id == user_id)
                .map(|m| (m.name.clone(), m.role))
        } else {
            return false;
        };

        let (member_name, old_role) = match change_info {
            Some(info) => info,
            None => return false,
        };

        // Now make the change
        if let Some(team) = self.teams.get_mut(team_id) {
            if let Some(member) = team.members.iter_mut().find(|m| m.user_id == user_id) {
                member.role = new_role;
            }
        }

        // Create event outside the borrow
        let event = self.create_activity(
            ActivityType::MemberRoleChanged,
            team_id,
            None,
            &format!("{}'s role changed from {:?} to {:?}", member_name, old_role, new_role),
        );
        if let Some(e) = event {
            self.activities.push(e);
        }
        true
    }

    // ==========================================================================
    // Sharing Operations
    // ==========================================================================

    /// Share an item
    pub fn share_item(
        &mut self,
        item_type: SharedItemType,
        item_id: &str,
        title: &str,
        team_id: Option<&str>,
    ) -> Option<String> {
        let user = self.current_user.as_ref()?;

        let share_id = format!("share_{}", chrono::Utc::now().timestamp_millis());
        let shared_item = SharedItem {
            id: share_id.clone(),
            item_type,
            item_id: item_id.to_string(),
            title: title.to_string(),
            description: None,
            owner_id: user.id.clone(),
            team_id: team_id.map(|s| s.to_string()),
            shares: Vec::new(),
            public_link: None,
            created_at: Utc::now(),
            modified_at: Utc::now(),
            version: 1,
            tags: Vec::new(),
        };

        self.shared_items.insert(share_id.clone(), shared_item);

        if let Some(tid) = team_id {
            let event = self.create_activity(
                ActivityType::ItemShared,
                tid,
                Some(title),
                &format!("shared \"{}\"", title),
            );
            if let Some(e) = event {
                self.activities.push(e);
            }
        }

        Some(share_id)
    }

    /// Share with specific user
    pub fn share_with_user(&mut self, share_id: &str, user_email: &str, permission: SharingPermission) -> bool {
        let sharer_id = match &self.current_user {
            Some(u) => u.id.clone(),
            None => return false,
        };

        if let Some(item) = self.shared_items.get_mut(share_id) {
            item.shares.push(Share {
                recipient: user_email.to_string(),
                permission,
                shared_at: Utc::now(),
                shared_by: sharer_id,
            });
            item.modified_at = Utc::now();
            return true;
        }
        false
    }

    /// Generate public link
    pub fn create_public_link(&mut self, share_id: &str) -> Option<String> {
        if let Some(item) = self.shared_items.get_mut(share_id) {
            let link = format!("https://share.example.com/{}", uuid::Uuid::new_v4());
            item.public_link = Some(link.clone());
            item.modified_at = Utc::now();
            return Some(link);
        }
        None
    }

    /// Remove public link
    pub fn remove_public_link(&mut self, share_id: &str) -> bool {
        if let Some(item) = self.shared_items.get_mut(share_id) {
            item.public_link = None;
            item.modified_at = Utc::now();
            return true;
        }
        false
    }

    /// Get shared item
    pub fn get_shared(&self, share_id: &str) -> Option<&SharedItem> {
        self.shared_items.get(share_id)
    }

    /// List shared items for team
    pub fn list_team_shared(&self, team_id: &str) -> Vec<&SharedItem> {
        self.shared_items.values()
            .filter(|i| i.team_id.as_deref() == Some(team_id))
            .collect()
    }

    /// List user's shared items
    pub fn list_my_shared(&self) -> Vec<&SharedItem> {
        let user_id = match &self.current_user {
            Some(u) => &u.id,
            None => return Vec::new(),
        };

        self.shared_items.values()
            .filter(|i| i.owner_id == *user_id)
            .collect()
    }

    /// List items shared with user
    pub fn list_shared_with_me(&self) -> Vec<&SharedItem> {
        let email = match &self.current_user {
            Some(u) => &u.email,
            None => return Vec::new(),
        };

        self.shared_items.values()
            .filter(|i| i.shares.iter().any(|s| s.recipient == *email))
            .collect()
    }

    /// Unshare item
    pub fn unshare(&mut self, share_id: &str) -> bool {
        self.shared_items.remove(share_id).is_some()
    }

    // ==========================================================================
    // Activity Feed
    // ==========================================================================

    /// Get activity feed for team
    pub fn get_activity(&self, team_id: &str, limit: usize) -> Vec<&ActivityEvent> {
        let mut activities: Vec<_> = self.activities.iter()
            .filter(|a| a.team_id == team_id)
            .collect();
        activities.sort_by(|a, b| b.timestamp.cmp(&a.timestamp));
        activities.truncate(limit);
        activities
    }

    /// Create activity event
    fn create_activity(
        &self,
        event_type: ActivityType,
        team_id: &str,
        item_title: Option<&str>,
        description: &str,
    ) -> Option<ActivityEvent> {
        let user = self.current_user.as_ref()?;

        Some(ActivityEvent {
            id: format!("activity_{}", chrono::Utc::now().timestamp_nanos_opt().unwrap_or(0)),
            event_type,
            user_id: user.id.clone(),
            user_name: user.name.clone(),
            item_id: None,
            item_title: item_title.map(|s| s.to_string()),
            description: description.to_string(),
            timestamp: Utc::now(),
            team_id: team_id.to_string(),
        })
    }

    // ==========================================================================
    // Permissions
    // ==========================================================================

    /// Check if user can edit item
    pub fn can_edit(&self, share_id: &str) -> bool {
        let user = match &self.current_user {
            Some(u) => u,
            None => return false,
        };

        if let Some(item) = self.shared_items.get(share_id) {
            // Owner can always edit
            if item.owner_id == user.id {
                return true;
            }

            // Check direct shares
            if let Some(share) = item.shares.iter().find(|s| s.recipient == user.email) {
                return matches!(share.permission, SharingPermission::Edit | SharingPermission::Admin);
            }

            // Check team membership
            if let Some(team_id) = &item.team_id {
                if let Some(team) = self.teams.get(team_id) {
                    if let Some(member) = team.members.iter().find(|m| m.user_id == user.id) {
                        return member.role.can_edit();
                    }
                }
            }
        }

        false
    }

    /// Check if user can view item
    pub fn can_view(&self, share_id: &str) -> bool {
        let user = match &self.current_user {
            Some(u) => u,
            None => return false,
        };

        if let Some(item) = self.shared_items.get(share_id) {
            // Owner can always view
            if item.owner_id == user.id {
                return true;
            }

            // Public link means anyone can view
            if item.public_link.is_some() {
                return true;
            }

            // Check direct shares
            if item.shares.iter().any(|s| s.recipient == user.email) {
                return true;
            }

            // Check team membership
            if let Some(team_id) = &item.team_id {
                if let Some(team) = self.teams.get(team_id) {
                    return team.members.iter().any(|m| m.user_id == user.id);
                }
            }
        }

        false
    }
}

impl Default for TeamManager {
    fn default() -> Self {
        Self::new()
    }
}

// =============================================================================
// GLOBAL INSTANCE
// =============================================================================

lazy_static::lazy_static! {
    static ref TEAM_MANAGER: Arc<Mutex<TeamManager>> =
        Arc::new(Mutex::new(TeamManager::new()));
}

/// Get the global team manager
pub fn teams() -> Arc<Mutex<TeamManager>> {
    TEAM_MANAGER.clone()
}

/// Set current user
pub fn set_user(id: &str, name: &str, email: &str) {
    TEAM_MANAGER.lock().unwrap().set_user(CurrentUser {
        id: id.to_string(),
        name: name.to_string(),
        email: email.to_string(),
    });
}

/// Create a team
pub fn create_team(name: &str) -> Option<String> {
    TEAM_MANAGER.lock().unwrap().create_team(name, None).map(|t| t.id.clone())
}

/// Share an item with a team
pub fn share_with_team(item_type: SharedItemType, item_id: &str, title: &str, team_id: &str) -> Option<String> {
    TEAM_MANAGER.lock().unwrap().share_item(item_type, item_id, title, Some(team_id))
}

// =============================================================================
// TESTS
// =============================================================================

#[cfg(test)]
mod tests {
    use super::*;

    fn setup_manager() -> TeamManager {
        let mut manager = TeamManager::new();
        manager.set_user(CurrentUser {
            id: "user1".to_string(),
            name: "Test User".to_string(),
            email: "test@example.com".to_string(),
        });
        manager
    }

    #[test]
    fn test_create_team() {
        let mut manager = setup_manager();
        let team = manager.create_team("Test Team", Some("A test team")).unwrap();

        assert_eq!(team.name, "Test Team");
        assert_eq!(team.members.len(), 1);
        assert_eq!(team.members[0].role, TeamRole::Owner);
    }

    #[test]
    fn test_add_member() {
        let mut manager = setup_manager();
        let team = manager.create_team("Test Team", None).unwrap();
        let team_id = team.id.clone();

        let result = manager.add_member(&team_id, TeamMember {
            user_id: "user2".to_string(),
            name: "User 2".to_string(),
            email: "user2@example.com".to_string(),
            role: TeamRole::Member,
            joined_at: Utc::now(),
            last_active: None,
        });

        assert!(result);
        assert_eq!(manager.get_team(&team_id).unwrap().members.len(), 2);
    }

    #[test]
    fn test_share_item() {
        let mut manager = setup_manager();
        let team = manager.create_team("Test Team", None).unwrap();
        let team_id = team.id.clone();

        let share_id = manager.share_item(
            SharedItemType::Workflow,
            "workflow_123",
            "My Workflow",
            Some(&team_id),
        ).unwrap();

        let shared = manager.get_shared(&share_id).unwrap();
        assert_eq!(shared.title, "My Workflow");
        assert_eq!(shared.team_id, Some(team_id));
    }

    #[test]
    fn test_share_with_user() {
        let mut manager = setup_manager();

        let share_id = manager.share_item(
            SharedItemType::Command,
            "cmd_123",
            "Useful Command",
            None,
        ).unwrap();

        manager.share_with_user(&share_id, "other@example.com", SharingPermission::Edit);

        let shared = manager.get_shared(&share_id).unwrap();
        assert_eq!(shared.shares.len(), 1);
        assert_eq!(shared.shares[0].recipient, "other@example.com");
    }

    #[test]
    fn test_public_link() {
        let mut manager = setup_manager();

        let share_id = manager.share_item(
            SharedItemType::Notebook,
            "nb_123",
            "Public Notebook",
            None,
        ).unwrap();

        let link = manager.create_public_link(&share_id).unwrap();
        assert!(link.starts_with("https://"));

        let shared = manager.get_shared(&share_id).unwrap();
        assert!(shared.public_link.is_some());
    }

    #[test]
    fn test_permissions() {
        let mut manager = setup_manager();

        let share_id = manager.share_item(
            SharedItemType::Workflow,
            "wf_123",
            "Test",
            None,
        ).unwrap();

        // Owner can edit
        assert!(manager.can_edit(&share_id));

        // Share with view-only
        manager.share_with_user(&share_id, "viewer@example.com", SharingPermission::View);

        // Change user
        manager.set_user(CurrentUser {
            id: "user2".to_string(),
            name: "Viewer".to_string(),
            email: "viewer@example.com".to_string(),
        });

        assert!(manager.can_view(&share_id));
        assert!(!manager.can_edit(&share_id));
    }

    #[test]
    fn test_activity_feed() {
        let mut manager = setup_manager();
        let team = manager.create_team("Test Team", None).unwrap();
        let team_id = team.id.clone();

        manager.add_member(&team_id, TeamMember {
            user_id: "user2".to_string(),
            name: "User 2".to_string(),
            email: "user2@example.com".to_string(),
            role: TeamRole::Member,
            joined_at: Utc::now(),
            last_active: None,
        });

        let activities = manager.get_activity(&team_id, 10);
        assert!(!activities.is_empty());
        assert!(activities.iter().any(|a| a.event_type == ActivityType::MemberJoined));
    }
}
