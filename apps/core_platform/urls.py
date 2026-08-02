from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import users, projects, versions, configuration, users_test, projects_list, organizations, rbac
from .views.users import CookieTokenRefreshView

router = DefaultRouter()
router.register(r'configuration/parameters', configuration.GlobalParameterViewSet)
router.register(r'configuration/common-methods', configuration.CommonMethodViewSet)
router.register(r'organizations', organizations.OrganizationViewSet)
router.register(r'roles', rbac.RoleViewSet)
router.register(r'permissions', rbac.PermissionViewSet)
router.register(r'user-roles', rbac.UserRoleViewSet)
router.register(r'audit', rbac.AuditLogViewSet)

urlpatterns = [
    # Users URLs
    path('users/me/', users.get_current_user, name='get_current_user'),
    path('users/register/', users.RegisterView.as_view(), name='register'),
    path('users/test-register/', users_test.test_register, name='test-register'),
    path('users/login/', users.login_view, name='login'),
    path('users/logout/', users.logout_view, name='logout'),
    path('users/token/refresh/', CookieTokenRefreshView.as_view(), name='token_refresh'),
    path('users/profile/', users.profile_view, name='profile'),
    path('users/list/', users.UserListView.as_view(), name='user-list'),
    path('users/<int:pk>/', users.UserDetailView.as_view(), name='user-detail'),
    
    # Projects URLs
    path('projects/', projects.ProjectListCreateView.as_view(), name='project-list'),
    path('projects/all/', projects.get_all_projects, name='all-projects'),
    path('projects/list/', projects_list.user_projects_list, name='user-projects-list'),
    path('projects/<int:pk>/', projects.ProjectDetailView.as_view(), name='project-detail'),
    path('projects/<int:project_id>/members/', projects.get_project_members, name='get-project-members'),
    path('projects/<int:project_id>/members/add/', projects.add_project_member, name='add-member'),
    path('projects/<int:project_id>/members/<int:member_id>/', projects.remove_project_member, name='remove-member'),
    path('projects/<int:project_id>/environments/', projects.ProjectEnvironmentListCreateView.as_view(), name='environment-list'),
    path('projects/<int:project_id>/statistics/', projects.get_project_statistics, name='project-statistics'),
    
    # Versions URLs
    path('versions/', versions.VersionListCreateView.as_view(), name='version-list'),
    path('versions/<int:pk>/', versions.VersionDetailView.as_view(), name='version-detail'),
    path('versions/projects/<int:project_id>/', versions.get_project_versions, name='project-versions'),
    
    # Configuration URLs (Router)
    path('', include(router.urls)),
]
