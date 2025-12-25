# Claude Skills Locations on Your Computer

## Main Skills Directories

### Agent Skills (140 total)
**Location**: `C:\Users\User\.claude\agents\`

All `.md` files in this directory are Claude agent skills including:
- playwright-expert.md
- python-expert.md
- backend-architect.md
- web-dev.md
- devops-automator.md
- docker-expert.md
- test-writer-fixer.md
- bug-detective.md
- debugger.md
- And 131+ more...

### Plugin/Command Skills (116 total)
**Location**: `C:\Users\User\.claude\awesome-claude-code-plugins-main\plugins\`

Each subdirectory contains a `.claude-plugin\` folder with plugin.json:
- explore
- plan
- analyze-codebase
- bug-fix
- optimize
- test-writer-fixer
- documentation-generator
- deployment-engineer
- And 108+ more...

### Skills for Your Akamai Bypass Project

**Web Scraping & Browser Automation**:
- `C:\Users\User\.claude\agents\playwright-expert.md`
- `C:\Users\User\.claude\agents\puppeteer-expert.md`
- `C:\Users\User\.claude\awesome-claude-code-plugins-main\plugins\web-dev\.claude-plugin\`

**Backend & API**:
- `C:\Users\User\.claude\agents\backend-architect.md`
- `C:\Users\User\.claude\agents\python-expert.md`
- `C:\Users\User\.claude\agents\nodejs-expert.md`

**DevOps & Infrastructure**:
- `C:\Users\User\.claude\agents\devops-automator.md`
- `C:\Users\User\.claude\agents\docker-expert.md`
- `C:\Users\User\.claude\awesome-claude-code-plugins-main\plugins\deployment-engineer\.claude-plugin\`

**Testing & Debugging**:
- `C:\Users\User\.claude\agents\test-writer-fixer.md`
- `C:\Users\User\.claude\awesome-claude-code-plugins-main\plugins\bug-detective\.claude-plugin\`

**Code Quality**:
- `C:\Users\User\.claude\agents\pragmatic-code-review-subagent.md`

## How to Use Skills in Claude Code CLI

For agent skills, use the Task tool:
```
Task(subagent_type="playwright-expert", prompt="Help me with browser automation")
```

For plugin skills, use the Skill tool:
```
Skill(skill="analyze-codebase")
```

## Complete List Command

To see all skills:
```bash
# Agent skills
ls ~/.claude/agents/*.md

# Plugin skills
ls ~/.claude/awesome-claude-code-plugins-main/plugins/*/
```
