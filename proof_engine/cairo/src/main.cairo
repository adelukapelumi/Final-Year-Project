#[executable]
fn main(vote_value: u32, registered_flag: u32, already_voted_flag: u32) -> u32 {
    let binary_constraint = vote_value * (vote_value - 1);
    assert(binary_constraint == 0, 'vote_value must be binary');
    assert(registered_flag == 1, 'registered_flag must be 1');
    assert(already_voted_flag == 0, 'already_voted_flag must be 0');

    let accepted = registered_flag * (1_u32 - already_voted_flag);
    assert(accepted == 1, 'accepted must be 1');
    accepted
}
