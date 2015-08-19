# Braviz Messages

## Subject

Communicate a change of the current focus subject

### Syntax:

```javascript
{
type : "subject",
subject : <subj_id>
}
```

## Sample

Communicate a change in the current focus sample

### Syntax

For all processes
```javascript
{
type : "sample",
sample : <subjects list>
}
```

For a single process
```javascript
{
type : "sample",
sample : <subjects list>,
target : <pid_of target application>
}
```

## Log

Communicate data about user actions. Include application state (scenario), so that the state can be revisited.

### Syntax

```javascript
{
type : "log",
action: <description of user action>,
state : <resulting state of the application>,
pid : <pid_of target application|id browser session>,
application :  <name of application>,
time : timestamp when the action happened
}
```

Example

```javascript
{
type: "log",
action: subject changed,
state : {current_subject: 10, variables: [45, 14,32], plot: ['scatter']},
pid : 1546,
application : 'anova',
time : 105130014
}
```

