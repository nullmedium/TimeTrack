# Table Styles Migration Guide

This guide helps migrate from the old scattered table styles to the new consolidated table system.

## Overview

The new consolidated table system provides:
- A single base `.table` class with all common styles
- Modifier classes for variations (hover, striped, compact, etc.)
- Consistent spacing and colors using CSS variables
- Better dark mode support
- Mobile-responsive options

## Migration Steps

### 1. Include the new CSS file

Add to your base template (layout.html):
```html
<link rel="stylesheet" href="{{ url_for('static', filename='css/tables-consolidated.css') }}">
```

### 2. Update Table Classes

#### Basic Tables

**Old:**
```html
<table class="data-table">
<table class="users-table">
<table class="projects-table">
```

**New:**
```html
<table class="table table--hover">
```

#### Time Entries Table

**Old:**
```html
<table class="entries-table">
```

**New:**
```html
<table class="table table--hover table--time-entries">
```

#### Admin Tables

**Old:**
```html
<table class="users-table">
<table class="projects-table">
```

**New:**
```html
<table class="table table--hover table--admin">
```

### 3. Add Container Classes

Wrap tables in proper containers for better styling:

```html
<div class="table-container">
    <div class="table-responsive">
        <table class="table table--hover">
            <!-- table content -->
        </table>
    </div>
</div>
```

### 4. Update Table Components

#### Actions Column

**Old:**
```html
<td>
    <div class="table-actions">
        <button>Edit</button>
        <button>Delete</button>
    </div>
</td>
```

**New:**
```html
<td class="actions-cell">
    <div class="table-actions">
        <button class="btn btn--sm">Edit</button>
        <button class="btn btn--sm btn--danger">Delete</button>
    </div>
</td>
```

#### Status Badges

**Old:**
```html
<span class="status-badge active">Active</span>
```

**New:**
```html
<span class="table-badge table-badge--success">Active</span>
```

### 5. Mobile Optimization

For better mobile display, add data attributes:

```html
<table class="table table--hover table--mobile-stack">
    <tbody>
        <tr>
            <td data-label="Name">John Doe</td>
            <td data-label="Email">john@example.com</td>
            <td data-label="Status">
                <span class="table-badge table-badge--success">Active</span>
            </td>
        </tr>
    </tbody>
</table>
```

## Available Modifier Classes

### Base Modifiers
- `.table--hover` - Adds hover effect to rows
- `.table--striped` - Alternating row colors
- `.table--bordered` - Adds borders to all cells
- `.table--compact` - Reduces padding
- `.table--sm` - Smaller font size
- `.table--fixed` - Fixed table layout

### Specialized Modifiers
- `.table--time-entries` - Time tracking table styling
- `.table--admin` - Admin panel tables
- `.table--data` - Data-heavy tables
- `.table--mobile-stack` - Stacks on mobile

### Responsive Options
- `.table-responsive` - Horizontal scroll on small screens
- `.table--scroll-body` - Fixed header with scrollable body

## Examples

### Basic Data Table
```html
<div class="table-container">
    <table class="table table--hover table--striped">
        <thead>
            <tr>
                <th>Name</th>
                <th>Email</th>
                <th>Actions</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td>John Doe</td>
                <td>john@example.com</td>
                <td class="actions-cell">
                    <div class="table-actions">
                        <button class="btn btn--sm">Edit</button>
                    </div>
                </td>
            </tr>
        </tbody>
    </table>
</div>
```

### Time Entries Table
```html
<div class="table-responsive">
    <table class="table table--hover table--time-entries">
        <thead>
            <tr>
                <th>Date</th>
                <th>Time</th>
                <th>Duration</th>
                <th>Project</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td class="date-cell">
                    <span class="date-day">15</span>
                    <span class="date-month">JAN</span>
                </td>
                <td class="time-cell">09:00 - 17:00</td>
                <td class="duration-cell">8h 00m</td>
                <td>TimeTrack Development</td>
            </tr>
        </tbody>
    </table>
</div>
```

### Mobile-Friendly Table
```html
<div class="table-container">
    <table class="table table--hover table--mobile-stack">
        <thead>
            <tr>
                <th>User</th>
                <th>Role</th>
                <th>Status</th>
                <th>Actions</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td data-label="User">
                    <img src="avatar.jpg" class="table-avatar" alt="">
                    Jane Smith
                </td>
                <td data-label="Role">Administrator</td>
                <td data-label="Status">
                    <span class="table-badge table-badge--success">Active</span>
                </td>
                <td data-label="Actions" class="actions-cell">
                    <div class="table-actions">
                        <button class="btn btn--sm">Edit</button>
                    </div>
                </td>
            </tr>
        </tbody>
    </table>
</div>
```

## Removing Old Styles

Once migration is complete, the following CSS can be removed:

1. From `style.css`:
   - `.data-table` definitions (lines 1510-1537)
   - `.users-table, .projects-table` definitions (lines 1286-1313)
   - `.time-history` definitions (lines 788-815)

2. From `time-tracking.css`:
   - `.entries-table` definitions (lines 334-355)

3. From dark mode CSS:
   - Individual table class overrides can be simplified

## Testing Checklist

- [ ] All tables display correctly in light mode
- [ ] All tables display correctly in dark mode
- [ ] Hover effects work
- [ ] Mobile responsiveness works
- [ ] Table actions are clickable
- [ ] Badges and status indicators display correctly
- [ ] No visual regressions from previous implementation