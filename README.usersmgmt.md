# User Management

This is the user management system of home podcast server, you need this for:
- adding notes
- editing playlist names
- episode titles.

## Examples

### Adding users can be done via the cmd

```bash
uv run usermgmt.py add -u admin -p secretpassword
```

### Reset password

```bash
uv run usermgmt.py reset -u admin 
```


### Delete users

```bash
uv run usermgmt.py del -u admin --force
```

### List users

```bash
uv run usermgmt.py list
```