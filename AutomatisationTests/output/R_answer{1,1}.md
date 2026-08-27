# Verified definition of `R2`

## Parameters

- `n`: fixed at `1`
- `k`: fixed at `1`

## Verified equivalence

$$
\mathtt{R2}_{\mathit{n},\mathit{k}}\left(\mathit{x},\mathit{y}\right) \Leftrightarrow \left(\left(\mathit{x} \neq \mathit{y}\right) \land \left(\exists \mathit{z}\in\mathbb{Z}^{2}\;\exists \mathit{w}\in\mathbb{Z}^{2}\;\left(\left(\mathit{z} \neq \mathit{w}\right) \land \mathtt{R1}\left(\mathit{x},\mathit{z}\right) \land \mathtt{R1}\left(\mathit{z},\mathit{y}\right) \land \mathtt{R1}\left(\mathit{x},\mathit{w}\right) \land \mathtt{R1}\left(\mathit{w},\mathit{y}\right)\right)\right)\right)
$$

## Candidate source

```text
(and (distinct x y) (exists ((z Point) (w Point)) (and (distinct z w) (R1 x z) (R1 z y) (R1 x w) (R1 w y))))
```
