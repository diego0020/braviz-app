# Braviz Messages

## Subject

Communicate a change of the current focus subject

### Syntax:

```javascript
    {
    subject : <subj_id>
    }
```

## Sample

Communicate a change in the current focus sample

### Syntax

For all processes
```javascript
{
sample : <subjects list>
}
```

For a single process
```javascript
{
sample : <subjects list>,
target : <pid_of target application
}
```
