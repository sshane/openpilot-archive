# dynamic-follow for openpilot

#### This branch is Arne's dynamic follow branch, but all new updates see the light of day here first, then if they work as expected, they are merged to [Arne's](https://github.com/arne182/openpilot/tree/dynamic-follow).

### How it works:

dynamic-follow uses multiple factors when deciding how far your car should be from the lead car. Stock openpilot (pre 0.5.10) uses a hard coded value of 1.8 seconds to determine the distance. This is fine for highway driving in the most perfect of situations where there is usually no traffic. However, in real life use, you expect your car to be able to naturally respond to unexpected (and expected) situations.

### Factors:

1. Speed:
    - Your car's speed is largely the most influential factor in generating a following distance. The faster you're going, the farther the distance in seconds it's set. Here's the current dynamic-follow velocity array (x in m/s, y in seconds):
    
    ```
    x = [0.0, 1.86267, 3.72533, 5.588, 7.45067, 9.31333, 11.55978, 13.645, 22.352, 31.2928, 33.528, 35.7632, 40.2336]  # velocity
    y = [1.03, 1.05363, 1.07879, 1.11493, 1.16969, 1.25071, 1.36325, 1.43, 1.6, 1.7, 1.75618, 1.85, 2.0]  # distances
    ```
    
    `Note, if you graph this, you can see a clear curve near the < 25 mph section of the array. This is to ensure a safe, smooth slow down to a stop.`

2. Relative velocity:
    - The relative velocity between your car and the car ahead is the second largest factor in deciding how far back your car should be. We use relative velocity as a factor because it can tell us if a car ahead is either; stopped and we need to slow down immediately, accelerating and we should speed up to go with the flow of traffic, or a number of other scenarios in between.
